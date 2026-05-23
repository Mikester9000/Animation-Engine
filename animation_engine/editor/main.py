"""
animation_engine.editor.main
================================
Tkinter-based Animation Editor.

The editor provides:
  - A scrollable Timeline panel for authoring keyframes.
  - A Bone Hierarchy panel showing the skeleton tree.
  - A Properties panel for editing keyframe values and material parameters.
  - File menu for New / Open / Save / Export to glTF.

The editor is intentionally lightweight (standard-library only) so that it
runs on any Python installation without GPU dependencies.  For AAA-quality
viewport rendering, integrate with Game Engine for Teaching's renderer.
"""

from __future__ import annotations

import json
import math
import os
from copy import deepcopy
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from ..model.model import Model
from ..model.material import PBRMaterial
from ..model.skeleton import Skeleton
from ..animation.clip import AnimationClip
from ..animation.channel import ChannelTarget
from ..animation.keyframe import KeyframeType
from ..animation.morph_track import MorphTrack
from ..io.anim_format import AnimExporter, AnimImporter
from ..io.gltf import GltfExporter
from ..math_utils import Matrix4x4, Vector3, Vector4, Quaternion, Transform
from ..runtime.skinning import cpu_skin_mesh
from .state import PlaybackState, is_rename_collision, merge_recent_files, normalize_path, select_clip_name, unique_duplicate_name

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_TITLE = "Animation Engine — Editor"
TIMELINE_HEIGHT = 180
TIMELINE_SECONDS = 10.0  # Default visible range in seconds
TIMELINE_PX_PER_SEC = 80  # Pixels per second on the timeline
RULER_HEIGHT = 20
HEADER_WIDTH = 150  # Width of the bone-name label column on the timeline
BG_COLOR = "#2b2b2b"
ACCENT_COLOR = "#e8a020"
TEXT_COLOR = "#dddddd"
GRID_COLOR = "#404040"
KF_COLOR = "#f0c040"
PLAYHEAD_COLOR = "#ff4444"
RECENT_FILES_LIMIT = 8

PS2_LIGHTING_PRESETS = {
    "ps2_studio": {
        "grid": "#33506f",
        "skeleton": "#f5d06a",
        "joint": "#f8e3a8",
        "wire": "#2a4a6a",
    },
    "ps2_field": {
        "grid": "#395539",
        "skeleton": "#d8d98f",
        "joint": "#f0efc3",
        "wire": "#375a37",
    },
    "ps2_night": {
        "grid": "#2d3550",
        "skeleton": "#8ab2ff",
        "joint": "#c7dbff",
        "wire": "#32466a",
    },
}


# ---------------------------------------------------------------------------
# Main Editor Window
# ---------------------------------------------------------------------------


class AnimationEditor:
    """
    Top-level editor application.

    Launch with::

        editor = AnimationEditor()
        editor.run()

    Or from the command line::

        python -m animation_engine.editor.main
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("1280x720")
        self.root.minsize(900, 560)

        # --- State ----------------------------------------------------------
        self.model: Optional[Model] = None
        self.clips: List[AnimationClip] = []
        self.morph_tracks: List[MorphTrack] = []
        self.active_clip: Optional[AnimationClip] = None
        self.playback = PlaybackState()
        self._after_id: Optional[str] = None
        self._current_file: Optional[str] = None
        self._recent_files: List[str] = []
        self._file_menu: Optional[tk.Menu] = None
        self._recent_menu: Optional[tk.Menu] = None
        self._document_metadata: dict = {}
        self._baseline_clip_snapshots: Dict[str, dict] = {}
        self._is_dirty: bool = False
        self._is_panning_view = False
        self._last_view_drag: Optional[tuple[int, int]] = None

        self.playback_speed_var = tk.StringVar(value="1.0")
        self.loop_var = tk.BooleanVar(value=True)
        self.compare_var = tk.BooleanVar(value=False)
        self.viewer_grid_var = tk.BooleanVar(value=True)
        self.viewer_lighting_var = tk.StringVar(value="ps2_studio")
        self.ik_mode_var = tk.BooleanVar(value=False)
        self._ik_target_bone: Optional[str] = None

        # Build UI
        self._build_menu()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit_requested)

        # New empty document on startup
        self._new_document()

    # -----------------------------------------------------------------------
    # Menu
    # -----------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        self._file_menu = file_menu
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self._new_document)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self._open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_file)
        file_menu.add_command(label="Save As…", command=self._save_file_as)
        self._recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self._recent_menu)
        self._rebuild_recent_files_menu()
        file_menu.add_separator()
        file_menu.add_command(label="Export glTF 2.0…", command=self._export_gltf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit_requested)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add Keyframe", accelerator="K", command=self._add_keyframe)
        edit_menu.add_command(
            label="Delete Keyframe", accelerator="Delete", command=self._delete_keyframe
        )
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Clip", command=self._add_clip)
        edit_menu.add_command(label="Rename Clip…", command=self._rename_clip)
        edit_menu.add_command(label="Duplicate Clip", command=self._duplicate_clip)
        edit_menu.add_command(label="Delete Clip", command=self._delete_clip)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Bone", command=self._add_bone)
        edit_menu.add_command(label="Rename Bone…", command=self._rename_bone)
        edit_menu.add_command(label="Delete Bone", command=self._delete_bone)
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Generate Clips from Profile…", command=self._generate_from_profile
        )
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Playback menu
        pb_menu = tk.Menu(menubar, tearoff=0)
        pb_menu.add_command(
            label="Play / Pause", accelerator="Space", command=self._toggle_playback
        )
        pb_menu.add_command(label="Stop", command=self._stop_playback)
        pb_menu.add_command(label="Go to Start", accelerator="Home", command=self._go_to_start)
        menubar.add_cascade(label="Playback", menu=pb_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Open Production Pack Builder…", command=self._launch_pack_builder
        )
        tools_menu.add_command(
            label="Validate Active File…", command=self._validate_active_file
        )
        tools_menu.add_separator()
        tools_menu.add_command(label="Clip Settings…", command=self._edit_clip_settings)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda _: self._new_document())
        self.root.bind("<Control-o>", lambda _: self._open_file())
        self.root.bind("<Control-s>", lambda _: self._save_file())
        self.root.bind("<space>", lambda _: self._toggle_playback())
        self.root.bind("<Home>", lambda _: self._go_to_start())
        self.root.bind("k", lambda _: self._add_keyframe())
        self.root.bind("<Control-Right>", lambda _: self._step_frame(1))
        self.root.bind("<Control-Left>", lambda _: self._step_frame(-1))

    # -----------------------------------------------------------------------
    # Layout
    # -----------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Build the three-panel layout: left bone tree, right properties, bottom timeline."""

        # -- Top toolbar --
        toolbar = tk.Frame(self.root, bg="#1e1e1e", height=36)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        self._build_toolbar(toolbar)

        # -- Main paned area --
        paned = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            bg=BG_COLOR,
            bd=0,
        )
        paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left: bone hierarchy + clip list
        left_frame = tk.Frame(paned, bg=BG_COLOR, width=220)
        paned.add(left_frame, minsize=140)
        self._build_left_panel(left_frame)

        # Centre: viewport placeholder
        centre_frame = tk.Frame(paned, bg="#1a1a1a", width=640)
        paned.add(centre_frame, minsize=300)
        self._build_centre_panel(centre_frame)

        # Right: properties
        right_frame = tk.Frame(paned, bg=BG_COLOR, width=240)
        paned.add(right_frame, minsize=160)
        self._build_right_panel(right_frame)

        # Bottom: timeline
        bottom_frame = tk.Frame(self.root, bg="#1e1e1e", height=TIMELINE_HEIGHT + 40)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self._build_timeline(bottom_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#111",
            fg=TEXT_COLOR,
            anchor="w",
            padx=6,
        )
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_toolbar(self, parent: tk.Frame) -> None:
        btn_cfg = dict(bg="#333", fg=TEXT_COLOR, relief=tk.FLAT, padx=8, pady=3)

        tk.Button(parent, text="⏮", command=self._go_to_start, **btn_cfg).pack(
            side=tk.LEFT, padx=2, pady=4
        )
        self.play_btn = tk.Button(parent, text="▶ Play", command=self._toggle_playback, **btn_cfg)
        self.play_btn.pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(parent, text="⏹", command=self._stop_playback, **btn_cfg).pack(
            side=tk.LEFT, padx=2, pady=4
        )
        tk.Button(parent, text="◀ Frame", command=lambda: self._step_frame(-1), **btn_cfg).pack(
            side=tk.LEFT, padx=2, pady=4
        )
        tk.Button(parent, text="Frame ▶", command=lambda: self._step_frame(1), **btn_cfg).pack(
            side=tk.LEFT, padx=2, pady=4
        )

        tk.Label(parent, text="  Time:", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT, padx=4)
        self.time_var = tk.StringVar(value="0.000 s")
        tk.Label(parent, textvariable=self.time_var, bg="#1e1e1e", fg=ACCENT_COLOR, width=9).pack(
            side=tk.LEFT
        )

        # Clip selector
        tk.Label(parent, text="  Clip:", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT, padx=4)
        self.clip_var = tk.StringVar()
        self.clip_combo = ttk.Combobox(
            parent, textvariable=self.clip_var, state="readonly", width=18
        )
        self.clip_combo.pack(side=tk.LEFT, padx=2, pady=4)
        self.clip_combo.bind("<<ComboboxSelected>>", self._on_clip_selected)

        tk.Checkbutton(
            parent,
            text="Loop",
            variable=self.loop_var,
            command=self._on_loop_toggled,
            bg="#1e1e1e",
            fg=TEXT_COLOR,
            selectcolor="#1e1e1e",
            activebackground="#1e1e1e",
            activeforeground=TEXT_COLOR,
        ).pack(side=tk.LEFT, padx=(8, 2))

        tk.Label(parent, text="Speed:", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(6, 2))
        speed_box = ttk.Combobox(
            parent,
            textvariable=self.playback_speed_var,
            values=["0.25", "0.5", "0.75", "1.0", "1.25", "1.5", "2.0"],
            state="readonly",
            width=5,
        )
        speed_box.pack(side=tk.LEFT, padx=(0, 6))
        speed_box.bind("<<ComboboxSelected>>", lambda _: self._sync_playback_controls())

    def _build_left_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Skeleton / Bones",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=("Helvetica", 9, "bold"),
        ).pack(fill=tk.X, padx=4, pady=(6, 2))

        self.bone_tree = ttk.Treeview(parent, show="tree", selectmode="browse")
        self.bone_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.bone_tree.bind("<<TreeviewSelect>>", self._on_bone_selected)
        self.bone_tree.bind("<Button-3>", self._on_bone_tree_right_click)
        self.bone_tree.bind("<Button-2>", self._on_bone_tree_right_click)

        # Style the treeview dark
        style = ttk.Style()
        style.configure(
            "Treeview",
            background="#252525",
            foreground=TEXT_COLOR,
            fieldbackground="#252525",
        )

        tk.Label(
            parent, text="Clip Browser", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4, pady=(6, 2))
        self.clip_listbox = tk.Listbox(
            parent,
            bg="#252525",
            fg=TEXT_COLOR,
            selectbackground=ACCENT_COLOR,
            relief=tk.FLAT,
            height=6,
            font=("Helvetica", 8),
        )
        self.clip_listbox.pack(fill=tk.X, padx=4, pady=(0, 6))
        self.clip_listbox.bind("<<ListboxSelect>>", self._on_clip_list_selected)
        self.clip_listbox.bind("<Button-3>", self._on_clip_list_right_click)
        self.clip_listbox.bind("<Button-2>", self._on_clip_list_right_click)

        # Clip settings strip (FPS, duration, motion_type)
        sep_clip = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep_clip.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(
            parent, text="Clip Settings", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4)
        self._clip_fps_var = tk.StringVar(value="30.0")
        self._clip_dur_var = tk.StringVar(value="0.000 s")
        self._clip_motion_var = tk.StringVar()
        self._clip_loop_left_var = tk.BooleanVar(value=True)
        for label, var, editable in [
            ("FPS", self._clip_fps_var, True),
            ("Duration", self._clip_dur_var, False),
            ("Motion Type", self._clip_motion_var, True),
        ]:
            row = tk.Frame(parent, bg=BG_COLOR)
            row.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(row, text=label + ":", bg=BG_COLOR, fg=TEXT_COLOR, width=10, anchor="e").pack(
                side=tk.LEFT
            )
            state = tk.NORMAL if editable else tk.DISABLED
            entry = tk.Entry(
                row, textvariable=var, bg="#333" if editable else "#252525",
                fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief=tk.FLAT,
                width=12, state=state,
            )
            entry.pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(
            parent, text="Loop", variable=self._clip_loop_left_var,
            command=self._on_clip_settings_loop_toggled,
            bg=BG_COLOR, fg=TEXT_COLOR, selectcolor=BG_COLOR,
            activebackground=BG_COLOR, activeforeground=TEXT_COLOR,
        ).pack(anchor="w", padx=4)
        tk.Button(
            parent, text="Apply Clip Settings", bg=ACCENT_COLOR, fg="#111",
            relief=tk.FLAT, command=self._apply_clip_settings,
        ).pack(fill=tk.X, padx=4, pady=(2, 6))

        # Morph Track browser
        sep_morph = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep_morph.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(
            parent, text="Morph Tracks", bg=BG_COLOR, fg=ACCENT_COLOR,
            font=("Helvetica", 9, "bold"),
        ).pack(fill=tk.X, padx=4)
        self.morph_listbox = tk.Listbox(
            parent, bg="#252525", fg=TEXT_COLOR, selectbackground=ACCENT_COLOR,
            relief=tk.FLAT, height=4, font=("Helvetica", 8),
        )
        self.morph_listbox.pack(fill=tk.X, padx=4, pady=(0, 2))
        morph_btn_row = tk.Frame(parent, bg=BG_COLOR)
        morph_btn_row.pack(fill=tk.X, padx=4, pady=(0, 4))
        tk.Button(
            morph_btn_row, text="Add", bg="#555", fg=TEXT_COLOR, relief=tk.FLAT, padx=4,
            command=self._add_morph_track,
        ).pack(side=tk.LEFT, padx=(0, 2))
        tk.Button(
            morph_btn_row, text="Add KF", bg="#555", fg=TEXT_COLOR, relief=tk.FLAT, padx=4,
            command=self._add_morph_keyframe,
        ).pack(side=tk.LEFT, padx=(0, 2))
        tk.Button(
            morph_btn_row, text="Remove", bg="#555", fg=TEXT_COLOR, relief=tk.FLAT, padx=4,
            command=self._remove_morph_track,
        ).pack(side=tk.LEFT)

    def _build_centre_panel(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg="#1a1a1a")
        header.pack(fill=tk.X, padx=6, pady=(6, 2))
        tk.Label(
            header,
            text="PS2 Preview Viewport",
            bg="#1a1a1a",
            fg=ACCENT_COLOR,
            font=("Helvetica", 9, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Combobox(
            header,
            textvariable=self.viewer_lighting_var,
            values=list(PS2_LIGHTING_PRESETS.keys()),
            state="readonly",
            width=12,
        ).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Checkbutton(
            header,
            text="Grid",
            variable=self.viewer_grid_var,
            command=self._redraw_viewport,
            bg="#1a1a1a",
            fg=TEXT_COLOR,
            selectcolor="#1a1a1a",
            activebackground="#1a1a1a",
            activeforeground=TEXT_COLOR,
        ).pack(side=tk.RIGHT, padx=6)
        tk.Checkbutton(
            header,
            text="Compare",
            variable=self.compare_var,
            command=self._redraw_viewport,
            bg="#1a1a1a",
            fg=TEXT_COLOR,
            selectcolor="#1a1a1a",
            activebackground="#1a1a1a",
            activeforeground=TEXT_COLOR,
        ).pack(side=tk.RIGHT, padx=6)

        tk.Checkbutton(
            header,
            text="IK",
            variable=self.ik_mode_var,
            command=self._redraw_viewport,
            bg="#1a1a1a",
            fg=TEXT_COLOR,
            selectcolor="#1a1a1a",
            activebackground="#1a1a1a",
            activeforeground=TEXT_COLOR,
        ).pack(side=tk.RIGHT, padx=6)

        self.viewport_canvas = tk.Canvas(parent, bg="#14181f", highlightthickness=0, cursor="fleur")
        self.viewport_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 6))
        self.viewport_canvas.bind("<Configure>", lambda _: self._redraw_viewport())
        self.viewport_canvas.bind("<ButtonPress-1>", self._on_viewport_drag_start)
        self.viewport_canvas.bind("<B1-Motion>", self._on_viewport_orbit_drag)
        self.viewport_canvas.bind("<Shift-B1-Motion>", self._on_viewport_pan_drag)
        self.viewport_canvas.bind("<ButtonRelease-1>", self._on_viewport_drag_end)
        self.viewport_canvas.bind("<MouseWheel>", self._on_viewport_zoom)
        self.viewport_canvas.bind("<Control-B1-Motion>", self._on_viewport_ik_drag)

        self._camera_yaw = 0.9
        self._camera_pitch = -0.25
        self._camera_distance = 4.5
        self._camera_pan = Vector3(0.0, 0.8, 0.0)

    def _build_right_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent, text="Properties", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4, pady=(6, 2))

        # Keyframe value fields
        fields = [
            ("Bone", "prop_bone"),
            ("Target", "prop_target"),
            ("Time (s)", "prop_time"),
            ("X", "prop_x"),
            ("Y", "prop_y"),
            ("Z", "prop_z"),
            ("W", "prop_w"),
            ("Interp", "prop_interp"),
        ]
        self._prop_vars: Dict[str, tk.StringVar] = {}
        for label, attr in fields:
            row = tk.Frame(parent, bg=BG_COLOR)
            row.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(row, text=label + ":", bg=BG_COLOR, fg=TEXT_COLOR, width=9, anchor="e").pack(
                side=tk.LEFT
            )
            var = tk.StringVar()
            self._prop_vars[attr] = var
            tk.Entry(
                row,
                textvariable=var,
                bg="#333",
                fg=TEXT_COLOR,
                insertbackground=TEXT_COLOR,
                relief=tk.FLAT,
                width=14,
            ).pack(side=tk.LEFT, padx=2)
        # Apply button
        tk.Button(
            parent,
            text="Apply Keyframe",
            bg=ACCENT_COLOR,
            fg="#111",
            relief=tk.FLAT,
            command=self._apply_keyframe_from_properties,
        ).pack(fill=tk.X, padx=4, pady=6)

        # Material section
        sep = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(
            parent, text="Material", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4)
        mat_fields = [
            ("Metallic", "mat_metallic"),
            ("Roughness", "mat_roughness"),
            ("Emissive R", "mat_em_r"),
            ("Emissive G", "mat_em_g"),
            ("Emissive B", "mat_em_b"),
        ]
        self._mat_vars: Dict[str, tk.StringVar] = {}
        for label, attr in mat_fields:
            row = tk.Frame(parent, bg=BG_COLOR)
            row.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(row, text=label + ":", bg=BG_COLOR, fg=TEXT_COLOR, width=11, anchor="e").pack(
                side=tk.LEFT
            )
            var = tk.StringVar(value="0.0")
            self._mat_vars[attr] = var
            tk.Entry(
                row,
                textvariable=var,
                bg="#333",
                fg=TEXT_COLOR,
                insertbackground=TEXT_COLOR,
                relief=tk.FLAT,
                width=10,
            ).pack(side=tk.LEFT, padx=2)

        # Events section
        sep2 = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep2.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(
            parent, text="Events", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4)

        ev_fields_row = tk.Frame(parent, bg=BG_COLOR)
        ev_fields_row.pack(fill=tk.X, padx=4, pady=1)
        self._ev_name_var = tk.StringVar()
        self._ev_time_var = tk.StringVar()
        tk.Label(ev_fields_row, text="Name:", bg=BG_COLOR, fg=TEXT_COLOR, width=6, anchor="e").pack(
            side=tk.LEFT
        )
        tk.Entry(
            ev_fields_row,
            textvariable=self._ev_name_var,
            bg="#333",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            width=10,
        ).pack(side=tk.LEFT, padx=2)
        tk.Label(ev_fields_row, text="t:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        tk.Entry(
            ev_fields_row,
            textvariable=self._ev_time_var,
            bg="#333",
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief=tk.FLAT,
            width=5,
        ).pack(side=tk.LEFT, padx=2)

        ev_btn_row = tk.Frame(parent, bg=BG_COLOR)
        ev_btn_row.pack(fill=tk.X, padx=4, pady=2)
        tk.Button(
            ev_btn_row,
            text="Add Event",
            bg=ACCENT_COLOR,
            fg="#111",
            relief=tk.FLAT,
            command=self._add_event,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            ev_btn_row,
            text="Remove",
            bg="#555",
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            command=self._remove_selected_event,
        ).pack(side=tk.LEFT, padx=2)

        self._event_listbox = tk.Listbox(
            parent,
            bg="#252525",
            fg=TEXT_COLOR,
            selectbackground=ACCENT_COLOR,
            relief=tk.FLAT,
            height=5,
            font=("Helvetica", 8),
        )
        self._event_listbox.pack(fill=tk.X, padx=4, pady=2)

        # F-curve editor (Task 24)
        self._build_curve_editor(parent)

        # State graph panel (Task 30)
        self._build_state_graph_panel(parent)

    # -----------------------------------------------------------------------
    # F-curve editor panel (Task 24)
    # -----------------------------------------------------------------------

    def _build_curve_editor(self, parent: tk.Frame) -> None:
        """Add a compact F-curve canvas to the right panel."""
        sep = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(
            parent, text="F-Curve", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(fill=tk.X, padx=4)
        self.curve_canvas = tk.Canvas(parent, bg="#1a1f2a", height=80, highlightthickness=0)
        self.curve_canvas.pack(fill=tk.X, padx=4, pady=(2, 4))
        self.curve_canvas.bind("<Configure>", lambda _: self._redraw_curve_editor())

    def _redraw_curve_editor(self) -> None:
        """Repaint the F-curve canvas for the active channel of the selected bone."""
        if not hasattr(self, "curve_canvas"):
            return
        c = self.curve_canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        c.create_rectangle(0, 0, w, h, fill="#1a1f2a", outline="")
        if not self.active_clip:
            c.create_text(w // 2, h // 2, text="no clip", fill="#7f8da0", font=("Helvetica", 8))
            return
        # Determine which channel to display (TRANSLATION then ROTATION fallback).
        bone_name = self._prop_vars.get("prop_bone", tk.StringVar()).get() if hasattr(self, "_prop_vars") else ""
        ch = None
        for target in (ChannelTarget.TRANSLATION, ChannelTarget.ROTATION, ChannelTarget.SCALE):
            ch = self.active_clip.get_channel(bone_name, target) if bone_name else None
            if ch:
                break
        if ch is None:
            # Fall back to first available channel in clip.
            for ch_key, ch_val in self.active_clip._channels.items():
                ch = ch_val
                break
        if ch is None or not ch.keyframes:
            c.create_text(w // 2, h // 2, text="no channel", fill="#7f8da0", font=("Helvetica", 8))
            return
        kf_times = [kf.time for kf in ch.keyframes]
        # Use first component (index 0) of each keyframe value.
        kf_vals = [kf.value[0] if isinstance(kf.value, (list, tuple)) else float(kf.value) for kf in ch.keyframes]
        t_min, t_max = min(kf_times), max(kf_times)
        v_min, v_max = min(kf_vals), max(kf_vals)
        t_range = t_max - t_min if t_max > t_min else 1.0
        v_range = v_max - v_min if abs(v_max - v_min) > 1e-6 else 1.0
        pad = 6

        def _tx(t: float) -> float:
            return pad + (t - t_min) / t_range * (w - 2 * pad)

        def _ty(v: float) -> float:
            return h - pad - (v - v_min) / v_range * (h - 2 * pad)

        # Draw horizontal zero line.
        y0 = _ty(0.0)
        if pad <= y0 <= h - pad:
            c.create_line(pad, y0, w - pad, y0, fill="#2d3a50", width=1)
        # Draw curve polyline.
        if len(kf_times) >= 2:
            n_steps = max(w, 60)
            pts: list[float] = []
            for i in range(n_steps + 1):
                t = t_min + i / n_steps * t_range
                v = ch.evaluate(t)
                val = v[0] if isinstance(v, (list, tuple)) else float(v)
                pts.extend([_tx(t), _ty(val)])
            c.create_line(*pts, fill="#e8a020", width=2, smooth=True)
        # Draw keyframe diamonds.
        for t, v in zip(kf_times, kf_vals):
            x, y = _tx(t), _ty(v)
            c.create_polygon(x, y - 4, x + 4, y, x, y + 4, x - 4, y, fill=KF_COLOR, outline="")
        # Label
        c.create_text(4, 4, text=f"{ch.bone_name}/{ch.target.name}[0]", anchor="nw", fill="#93a6c2", font=("Helvetica", 7))

    # -----------------------------------------------------------------------
    # State graph panel (Task 30)
    # -----------------------------------------------------------------------

    def _build_state_graph_panel(self, parent: tk.Frame) -> None:
        """Add a compact blend-tree state graph canvas to the right panel."""
        sep = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep.pack(fill=tk.X, padx=4, pady=4)
        hdr = tk.Frame(parent, bg=BG_COLOR)
        hdr.pack(fill=tk.X, padx=4)
        tk.Label(
            hdr, text="State Graph", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(side=tk.LEFT)
        tk.Button(
            hdr, text="↺", bg="#333", fg=TEXT_COLOR, relief=tk.FLAT, padx=4,
            command=self._redraw_state_graph,
        ).pack(side=tk.RIGHT)
        self.state_graph_canvas = tk.Canvas(parent, bg="#161d27", height=100, highlightthickness=0)
        self.state_graph_canvas.pack(fill=tk.X, padx=4, pady=(2, 4))
        self.state_graph_canvas.bind("<Configure>", lambda _: self._redraw_state_graph())

    def _redraw_state_graph(self) -> None:
        """Repaint the blend-tree state graph canvas."""
        if not hasattr(self, "state_graph_canvas"):
            return
        c = self.state_graph_canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        c.create_rectangle(0, 0, w, h, fill="#161d27", outline="")
        # Collect states from model blend tree if present.
        bt = getattr(self.model, "blend_tree", None) if self.model else None
        states: list[str] = []
        if bt is not None and hasattr(bt, "_states"):
            states = list(bt._states.keys())
        elif self.active_clip:
            states = [cl.name for cl in self.clips]
        if not states:
            c.create_text(w // 2, h // 2, text="no states", fill="#7f8da0", font=("Helvetica", 8))
            return
        # Layout states in a single row (or wrap) and draw labelled boxes.
        n = len(states)
        box_w = max(50, min(90, (w - 12) // max(1, n) - 8))
        box_h = 24
        col_step = box_w + 10
        row_h = box_h + 18
        cols = max(1, (w - 12) // col_step)
        positions: Dict[str, tuple[int, int]] = {}
        for idx, name in enumerate(states):
            col = idx % cols
            row = idx // cols
            x = 6 + col * col_step + box_w // 2
            y = 14 + row * row_h + box_h // 2
            positions[name] = (x, y)
            active = (self.active_clip and name == self.active_clip.name)
            fill = ACCENT_COLOR if active else "#2d3a50"
            c.create_rectangle(x - box_w // 2, y - box_h // 2, x + box_w // 2, y + box_h // 2,
                                fill=fill, outline="#93a6c2", width=1)
            c.create_text(x, y, text=name[:10], fill="#111" if active else TEXT_COLOR, font=("Helvetica", 7))
        # Draw transition arrows if blend tree available.
        if bt is not None and hasattr(bt, "_transitions"):
            for tr in bt._transitions:
                src = positions.get(getattr(tr, "from_state", None))
                dst = positions.get(getattr(tr, "to_state", None))
                if src and dst and src != dst:
                    c.create_line(src[0], src[1], dst[0], dst[1],
                                  fill="#93a6c2", arrow=tk.LAST, width=1)

    # -----------------------------------------------------------------------
    # IK posing mode (Task 25)
    # -----------------------------------------------------------------------

    def _on_viewport_ik_drag(self, event) -> None:
        """Handle Ctrl+drag in the viewport to apply IK when IK mode is enabled."""
        if not self.ik_mode_var.get():
            return
        if not self.model or not self.model.skeleton or not self.active_clip:
            return
        skel = self.model.skeleton
        if not skel.bones:
            return
        # Pick the last bone as IK end-effector by default; user can extend.
        if self._ik_target_bone is None:
            self._ik_target_bone = skel.bones[-1].name
        # Map 2-D screen drag delta to a rough 3-D world displacement.
        w = max(1, self.viewport_canvas.winfo_width())
        h = max(1, self.viewport_canvas.winfo_height())
        # Unproject screen point to an approximate XY world delta.
        fov = 1.1
        half_h = math.tan(fov * 0.5) * self._camera_distance
        half_w = half_h * (w / max(1, h))
        dx_world = (event.x / w - 0.5) * 2.0 * half_w
        dy_world = -(event.y / h - 0.5) * 2.0 * half_h
        target_world = Vector3(
            self._camera_pan.x + dx_world,
            self._camera_pan.y + dy_world,
            self._camera_pan.z,
        )
        self._apply_ik_pose(self._ik_target_bone, target_world)

    def _apply_ik_pose(self, end_bone_name: str, target_pos: Vector3) -> None:
        """Run one FABRIK pass and write resulting rotations into the active clip."""
        try:
            from ..animation.ik_solver import IKChain, IKSolver
        except Exception:
            return
        if not self.model or not self.model.skeleton or not self.active_clip:
            return
        skel = self.model.skeleton
        # Build the IK chain from root to end bone.
        chain_bones: list = []
        bone_map = {b.name: b for b in skel.bones}
        b = bone_map.get(end_bone_name)
        while b is not None:
            chain_bones.insert(0, b)
            if b.parent_index < 0:
                break
            b = skel.bones[b.parent_index]
        if len(chain_bones) < 2:
            return
        world_mats = self._evaluate_pose_world_matrices(self.active_clip, self.playback.time_seconds)
        # Build pose_transforms dict (world-space) for solver.
        pose_transforms: dict = {}
        for bone in chain_bones:
            pos = world_mats[bone.index].transform_point(Vector3.zero())
            from ..math_utils import Transform as _Transform
            pose_transforms[bone.name] = _Transform(pos)
        bone_lengths = []
        for i in range(len(chain_bones) - 1):
            p0 = pose_transforms[chain_bones[i].name].position
            p1 = pose_transforms[chain_bones[i + 1].name].position
            bone_lengths.append(max(1e-4, (p1 - p0).length()))
        chain = IKChain(
            bone_names=[b.name for b in chain_bones],
            target=target_pos,
            max_iterations=10,
            tolerance=1e-3,
        )
        IKSolver().solve(chain, pose_transforms, bone_lengths)
        # Write resulting rotations back as keyframes in the active clip.
        t = self.playback.time_seconds
        for bone in chain_bones:
            tr = pose_transforms.get(bone.name)
            if tr is not None:
                q = tr.rotation
                self.active_clip.add_keyframe(
                    bone.name, ChannelTarget.ROTATION, t, [q.x, q.y, q.z, q.w]
                )
        self._redraw_viewport()

    # -----------------------------------------------------------------------
    # Clip Settings helpers
    # -----------------------------------------------------------------------

    def _refresh_clip_settings(self) -> None:
        """Sync the Clip Settings strip with the active clip."""
        if not hasattr(self, "_clip_fps_var"):
            return
        clip = self.active_clip
        if clip is None:
            self._clip_fps_var.set("30.0")
            self._clip_dur_var.set("0.000 s")
            self._clip_motion_var.set("")
            return
        self._clip_fps_var.set(f"{clip.fps:.4g}")
        self._clip_dur_var.set(f"{clip.duration:.3f} s")
        motion = getattr(clip, "motion_type", "") or ""
        self._clip_motion_var.set(motion)
        self._clip_loop_left_var.set(bool(clip.loop))

    def _apply_clip_settings(self) -> None:
        """Write FPS and motion_type from the Clip Settings strip into the active clip."""
        if not self.active_clip:
            return
        try:
            fps = float(self._clip_fps_var.get())
            if fps <= 0.0:
                raise ValueError("FPS must be positive.")
            self.active_clip.fps = fps
        except ValueError as exc:
            messagebox.showwarning("Clip Settings", f"Invalid FPS: {exc}")
            return
        motion_type = self._clip_motion_var.get().strip()
        self.active_clip.motion_type = motion_type
        self.active_clip.loop = bool(self._clip_loop_left_var.get())
        self.loop_var.set(self.active_clip.loop)
        self._mark_dirty()
        self._refresh_clip_settings()
        self.status_var.set(
            f"Clip settings updated: fps={self.active_clip.fps}, motion_type={motion_type!r}"
        )

    def _on_clip_settings_loop_toggled(self) -> None:
        if self.active_clip:
            self.active_clip.loop = bool(self._clip_loop_left_var.get())
            self.loop_var.set(self.active_clip.loop)
            self._mark_dirty()

    def _edit_clip_settings(self) -> None:
        """Open Clip Settings dialog (keyboard shortcut / Tools menu)."""
        self._apply_clip_settings()

    # -----------------------------------------------------------------------
    # Morph Track helpers
    # -----------------------------------------------------------------------

    def _refresh_morph_track_list(self) -> None:
        """Sync the morph track listbox with the current morph_tracks list."""
        if not hasattr(self, "morph_listbox"):
            return
        self.morph_listbox.delete(0, tk.END)
        for mt in self.morph_tracks:
            kf_count = len(mt.keyframes)
            self.morph_listbox.insert(tk.END, f"{mt.morph_name}  ({kf_count} kf)")

    def _add_morph_track(self) -> None:
        """Prompt for a morph target name and create a new MorphTrack."""
        dialog = _SimpleDialog(self.root, title="Add Morph Track", prompt="Morph target name:")
        name = dialog.result
        if not name:
            return
        name = name.strip()
        if any(mt.morph_name == name for mt in self.morph_tracks):
            messagebox.showwarning("Add Morph Track", f"A track named '{name}' already exists.")
            return
        self.morph_tracks.append(MorphTrack(name))
        self._refresh_morph_track_list()
        self._mark_dirty()
        self.status_var.set(f"Added morph track '{name}'.")

    def _add_morph_keyframe(self) -> None:
        """Add a weight keyframe at the current playhead time for the selected morph track."""
        sel = self.morph_listbox.curselection()
        if not sel:
            messagebox.showinfo("Add Morph Keyframe", "Select a morph track first.")
            return
        mt = self.morph_tracks[sel[0]]
        dialog = _SimpleDialog(
            self.root, title="Morph Keyframe",
            prompt=f"Weight [0..1] for '{mt.morph_name}' at t={self.playback.time_seconds:.3f}s:"
        )
        if not dialog.result:
            return
        try:
            weight = float(dialog.result)
        except ValueError:
            messagebox.showwarning("Morph Keyframe", "Enter a numeric weight.")
            return
        raw_weight = float(dialog.result)
        weight = max(0.0, min(1.0, raw_weight))
        if weight != raw_weight:
            messagebox.showinfo(
                "Morph Keyframe", f"Weight clamped to {weight:.3f} (input {raw_weight:.3f})."
            )
        mt.add_keyframe(self.playback.time_seconds, weight)
        self._refresh_morph_track_list()
        self._mark_dirty()
        self.status_var.set(
            f"Morph keyframe: {mt.morph_name} weight={weight:.3f} t={self.playback.time_seconds:.3f}s"
        )

    def _remove_morph_track(self) -> None:
        """Remove the selected morph track."""
        sel = self.morph_listbox.curselection()
        if not sel:
            return
        mt = self.morph_tracks[sel[0]]
        confirmed = messagebox.askyesno(
            "Remove Morph Track", f"Delete morph track '{mt.morph_name}'?"
        )
        if confirmed:
            self.morph_tracks.pop(sel[0])
            self._refresh_morph_track_list()
            self._mark_dirty()

    # -----------------------------------------------------------------------
    # Tools menu handlers
    # -----------------------------------------------------------------------

    def _launch_pack_builder(self) -> None:
        """Open the Production Pack Builder as a separate process."""
        import subprocess
        import sys

        try:
            subprocess.Popen(
                [sys.executable, "-m", "animation_engine.gui.production_pack_gui"],
                close_fds=True,
            )
        except Exception as exc:
            messagebox.showerror("Production Pack Builder", str(exc))

    def _validate_active_file(self) -> None:
        """Run the CLI validate-clip command on the active file and show results."""
        if not self._current_file:
            messagebox.showinfo("Validate", "Save the file first before validating.")
            return
        import io
        from contextlib import redirect_stdout
        from animation_engine.cli import build_parser, _cmd_validate_clip

        parser = build_parser()
        buf = io.StringIO()
        try:
            args = parser.parse_args(["validate-clip", "--input", self._current_file])
            with redirect_stdout(buf):
                code = _cmd_validate_clip(args)
        except Exception as exc:
            messagebox.showerror("Validate", str(exc))
            return
        output = buf.getvalue()
        title = "Validation Passed" if code == 0 else "Validation Failed"
        if code == 0:
            messagebox.showinfo(title, output or "All clips valid.")
        else:
            messagebox.showerror(title, output or "Validation failed.")


    def _build_timeline(self, parent: tk.Frame) -> None:
        """Build the scrollable timeline strip."""
        tk.Label(
            parent, text="Timeline", bg="#1e1e1e", fg=ACCENT_COLOR, font=("Helvetica", 9, "bold")
        ).pack(side=tk.TOP, anchor="w", padx=6)

        scrub_row = tk.Frame(parent, bg="#1e1e1e")
        scrub_row.pack(fill=tk.X, padx=6, pady=(0, 4))
        tk.Label(scrub_row, text="Scrub", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.scrub_scale = tk.Scale(
            scrub_row,
            from_=0.0,
            to=TIMELINE_SECONDS,
            orient=tk.HORIZONTAL,
            resolution=0.001,
            showvalue=False,
            command=self._on_scrub_changed,
            length=360,
            bg="#1e1e1e",
            fg=TEXT_COLOR,
            highlightthickness=0,
            troughcolor="#2b2b2b",
        )
        self.scrub_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        timeline_outer = tk.Frame(parent, bg="#1e1e1e")
        timeline_outer.pack(fill=tk.BOTH, expand=True)

        h_scroll = tk.Scrollbar(timeline_outer, orient=tk.HORIZONTAL)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.timeline_canvas = tk.Canvas(
            timeline_outer,
            bg="#252525",
            height=TIMELINE_HEIGHT,
            xscrollcommand=h_scroll.set,
            cursor="crosshair",
        )
        self.timeline_canvas.pack(fill=tk.BOTH, expand=True)
        h_scroll.config(command=self.timeline_canvas.xview)

        self.timeline_canvas.bind("<ButtonPress-1>", self._on_timeline_click)
        self.timeline_canvas.bind("<Configure>", lambda _: self._redraw_timeline())

    # -----------------------------------------------------------------------
    # Timeline drawing
    # -----------------------------------------------------------------------

    def _redraw_timeline(self) -> None:
        """Repaint the entire timeline canvas."""
        c = self.timeline_canvas
        c.delete("all")

        height = c.winfo_height()

        total_px = int(TIMELINE_SECONDS * TIMELINE_PX_PER_SEC)
        c.configure(scrollregion=(0, 0, total_px + HEADER_WIDTH, height))

        # Ruler background
        c.create_rectangle(
            HEADER_WIDTH, 0, total_px + HEADER_WIDTH, RULER_HEIGHT, fill="#1a1a1a", outline=""
        )

        # Second tick marks and labels
        for sec in range(int(TIMELINE_SECONDS) + 1):
            x = HEADER_WIDTH + sec * TIMELINE_PX_PER_SEC
            c.create_line(x, 0, x, RULER_HEIGHT, fill=GRID_COLOR)
            c.create_text(
                x + 2,
                RULER_HEIGHT // 2,
                text=f"{sec}s",
                fill=TEXT_COLOR,
                anchor="w",
                font=("Helvetica", 7),
            )

        # Bone rows
        if self.active_clip and self.model and self.model.skeleton:
            bone_names = [b.name for b in self.model.skeleton.bones]
            row_height = max(20, (height - RULER_HEIGHT) // max(1, len(bone_names)))
            for row_idx, bone_name in enumerate(bone_names):
                y_top = RULER_HEIGHT + row_idx * row_height
                # Row background (alternating)
                row_bg = "#252525" if row_idx % 2 == 0 else "#2a2a2a"
                c.create_rectangle(
                    0, y_top, total_px + HEADER_WIDTH, y_top + row_height, fill=row_bg, outline=""
                )
                # Bone label
                c.create_text(
                    4,
                    y_top + row_height // 2,
                    text=bone_name,
                    fill=TEXT_COLOR,
                    anchor="w",
                    font=("Helvetica", 8),
                )

                # Keyframe diamonds for each channel
                for target in ChannelTarget:
                    ch = self.active_clip.get_channel(bone_name, target)
                    if ch is None:
                        continue
                    for kf in ch.keyframes:
                        kx = HEADER_WIDTH + kf.time * TIMELINE_PX_PER_SEC
                        ky = y_top + row_height // 2
                        r = 5
                        c.create_polygon(
                            kx,
                            ky - r,
                            kx + r,
                            ky,
                            kx,
                            ky + r,
                            kx - r,
                            ky,
                            fill=KF_COLOR,
                            outline="#fff",
                        )

        # Playhead
        px = HEADER_WIDTH + self.playback.time_seconds * TIMELINE_PX_PER_SEC
        c.create_line(px, 0, px, height, fill=PLAYHEAD_COLOR, width=2)
        c.create_polygon(px - 6, 0, px + 6, 0, px, 10, fill=PLAYHEAD_COLOR)

        # Event markers — drawn above the ruler as small downward triangles
        if self.active_clip:
            for ev in self.active_clip.get_events():
                ex = HEADER_WIDTH + ev["time"] * TIMELINE_PX_PER_SEC
                r = 6
                c.create_polygon(
                    ex - r,
                    0,
                    ex + r,
                    0,
                    ex,
                    r * 2,
                    fill="#ff8800",
                    outline="#fff",
                    width=1,
                )
                c.create_text(
                    ex,
                    r * 2 + 2,
                    text=ev["name"],
                    fill="#ff8800",
                    anchor="n",
                    font=("Helvetica", 6),
                )

    # -----------------------------------------------------------------------
    # Document management
    # -----------------------------------------------------------------------

    def _new_document(self) -> None:
        """Create an empty document with a minimal skeleton."""
        if not self._confirm_discard_unsaved("Create a new document?"):
            return
        self.model = Model("NewCharacter")

        # Default skeleton: root + spine hierarchy (minimal FF15-like rig)
        skel = Skeleton("Character")
        root_idx = skel.add_bone("root", parent_index=-1)
        pelvis_idx = skel.add_bone(
            "pelvis", parent_index=root_idx, local_transform=Transform(position=Vector3(0, 0.9, 0))
        )
        spine_01 = skel.add_bone(
            "spine_01",
            parent_index=pelvis_idx,
            local_transform=Transform(position=Vector3(0, 0.2, 0)),
        )
        skel.add_bone(
            "spine_02",
            parent_index=spine_01,
            local_transform=Transform(position=Vector3(0, 0.2, 0)),
        )
        skel.compute_bind_pose()
        self.model.skeleton = skel

        # Default material
        mat = PBRMaterial("skin")
        mat.albedo_color = [0.8, 0.65, 0.5, 1.0]
        mat.roughness = 0.7
        self.model.add_material(mat)

        # Default animation clip
        clip = AnimationClip("idle", fps=30.0, loop=True)
        clip.add_keyframe("pelvis", ChannelTarget.TRANSLATION, 0.0, [0, 0.9, 0])
        clip.add_keyframe("pelvis", ChannelTarget.TRANSLATION, 1.0, [0, 0.91, 0])
        clip.add_keyframe("pelvis", ChannelTarget.TRANSLATION, 2.0, [0, 0.9, 0])
        self.clips = [clip]
        self.morph_tracks = []
        self.active_clip = clip
        self._current_file = None
        self._document_metadata = {}
        self._baseline_clip_snapshots = {clip.name: deepcopy(clip.to_dict())}
        self.playback = PlaybackState()
        self.loop_var.set(bool(clip.loop))
        self._is_dirty = False

        self._update_title()
        self._refresh_ui()
        self.status_var.set("New document created.")

    def _refresh_ui(self) -> None:
        """Synchronise all UI widgets with the current document state."""
        # Clip combo
        clip_names = [c.name for c in self.clips]
        self.clip_combo["values"] = clip_names
        selected_name = self.active_clip.name if self.active_clip else ""
        selected_name = select_clip_name(clip_names, selected_name, "")
        self.clip_var.set(selected_name)
        self.clip_listbox.delete(0, tk.END)
        for clip_name in clip_names:
            self.clip_listbox.insert(tk.END, clip_name)
        if selected_name:
            try:
                idx = clip_names.index(selected_name)
                self.clip_listbox.selection_set(idx)
                self.clip_listbox.activate(idx)
            except ValueError:
                pass

        # Bone tree
        self.bone_tree.delete(*self.bone_tree.get_children())
        if self.model and self.model.skeleton:
            self._populate_bone_tree("", self.model.skeleton, -1)

        self._refresh_event_list()
        self._refresh_morph_track_list()
        self._refresh_clip_settings()
        self._sync_playback_controls()
        self._redraw_timeline()
        self._redraw_viewport()

    def _populate_bone_tree(self, parent_id: str, skel: Skeleton, parent_bone_idx: int) -> None:
        """Recursively insert bone nodes into the Treeview."""
        for bone in skel.bones:
            if bone.parent_index == parent_bone_idx:
                node_id = self.bone_tree.insert(parent_id, "end", iid=bone.name, text=bone.name)
                self._populate_bone_tree(node_id, skel, bone.index)

    # -----------------------------------------------------------------------
    # File operations
    # -----------------------------------------------------------------------

    def _open_file(self) -> None:
        if not self._confirm_discard_unsaved("Open another file?"):
            return
        path = filedialog.askopenfilename(
            title="Open Animation File",
            filetypes=[("Animation files", "*.anim"), ("All files", "*.*")],
        )
        if not path:
            return
        normalised_path = normalize_path(path)
        try:
            importer = AnimImporter()
            model, clips, morph_tracks, metadata = importer.import_file(
                normalised_path, include_metadata=True
            )
            self.model = model
            self.clips = clips
            self.morph_tracks = morph_tracks
            self.active_clip = clips[0] if clips else None
            self._current_file = normalised_path
            self._document_metadata = metadata or {}
            self._baseline_clip_snapshots = {clip.name: deepcopy(clip.to_dict()) for clip in clips}
            self._apply_editor_metadata()
            self._remember_recent_file(normalised_path)
            self._is_dirty = False
            self._update_title()
            self._refresh_ui()
            self.status_var.set(f"Opened: {normalised_path}")
        except (json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Open Error", f"Invalid or incompatible .anim file:\n{exc}")
        except Exception as exc:
            messagebox.showerror("Open Error", str(exc))

    def _save_file(self) -> None:
        if self._current_file:
            self._write_file(self._current_file)
        else:
            self._save_file_as()

    def _save_file_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Animation File",
            defaultextension=".anim",
            filetypes=[("Animation files", "*.anim"), ("All files", "*.*")],
        )
        if path:
            normalised_path = normalize_path(path)
            self._write_file(normalised_path)
            self._current_file = normalised_path
            self._remember_recent_file(normalised_path)
            self._update_title()

    def _write_file(self, path: str) -> None:
        try:
            exporter = AnimExporter()
            metadata = self._build_export_metadata()
            exporter.export(self.model, self.clips, self.morph_tracks, metadata, path)
            self._current_file = path
            self._remember_recent_file(path)
            self._baseline_clip_snapshots = {
                clip.name: deepcopy(clip.to_dict()) for clip in self.clips
            }
            self._is_dirty = False
            self._update_title()
            self.status_var.set(f"Saved: {path}")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))

    def _export_gltf(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export glTF 2.0",
            defaultextension=".gltf",
            filetypes=[("glTF files", "*.gltf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            exporter = GltfExporter()
            exporter.export(self.model, self.clips, path)
            self.status_var.set(f"Exported glTF: {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    # -----------------------------------------------------------------------
    # Playback
    # -----------------------------------------------------------------------

    def _toggle_playback(self) -> None:
        if self.playback.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        self._sync_playback_controls()
        self.playback.is_playing = True
        self.play_btn.config(text="⏸ Pause")
        self._tick()

    def _pause_playback(self) -> None:
        self.playback.is_playing = False
        self.play_btn.config(text="▶ Play")
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _stop_playback(self) -> None:
        self._pause_playback()
        self.playback.scrub(0.0)
        self.time_var.set("0.000 s")
        self.scrub_scale.set(0.0)
        self._redraw_timeline()
        self._redraw_viewport()

    def _go_to_start(self) -> None:
        self._stop_playback()

    def _tick(self) -> None:
        """Advance playback by one frame (30 fps target)."""
        if not self.playback.is_playing:
            return
        dt = 1.0 / 30.0
        dur = self._active_duration()
        self.playback.step(dt, dur, loop=self._active_loop())
        self.time_var.set(f"{self.playback.time_seconds:.3f} s")
        self.scrub_scale.set(self.playback.time_seconds)
        self._redraw_timeline()
        self._redraw_viewport()
        self._after_id = self.root.after(int(dt * 1000), self._tick)

    def _step_frame(self, direction: int = 1) -> None:
        self._pause_playback()
        frame_dt = (1.0 / 30.0) * (1 if direction >= 0 else -1)
        dur = self._active_duration()
        new_time = self.playback.time_seconds + frame_dt
        if dur > 0.0:
            if self._active_loop():
                new_time = new_time % dur
            else:
                new_time = max(0.0, min(dur, new_time))
        self.playback.scrub(new_time, self._active_duration())
        self.time_var.set(f"{self.playback.time_seconds:.3f} s")
        self.scrub_scale.set(self.playback.time_seconds)
        self._redraw_timeline()
        self._redraw_viewport()

    # -----------------------------------------------------------------------
    # Keyframe editing
    # -----------------------------------------------------------------------

    def _add_keyframe(self) -> None:
        """Add a keyframe at the current playback time for the selected bone."""
        if not self.active_clip or not self.model:
            return
        selected = self.bone_tree.focus()
        if not selected:
            messagebox.showinfo("Add Keyframe", "Select a bone first.")
            return
        # Default: add a rotation keyframe = identity at current time
        self.active_clip.add_keyframe(
            selected,
            ChannelTarget.ROTATION,
            self.playback.time_seconds,
            [0.0, 0.0, 0.0, 1.0],
        )
        self._redraw_timeline()
        self._redraw_viewport()
        self._mark_dirty()
        self.status_var.set(f"Added keyframe on {selected} at t={self.playback.time_seconds:.3f}s")

    def _delete_keyframe(self) -> None:
        """Remove the keyframe closest to the playhead for the selected bone."""
        if not self.active_clip:
            return
        selected = self.bone_tree.focus()
        if not selected:
            return
        for target in ChannelTarget:
            ch = self.active_clip.get_channel(selected, target)
            if ch:
                ch.remove_keyframe(self.playback.time_seconds)
        self._redraw_timeline()
        self._redraw_viewport()
        self._mark_dirty()

    def _apply_keyframe_from_properties(self) -> None:
        """Read values from the Properties panel and set a keyframe."""
        if not self.active_clip:
            return
        try:
            bone = self._prop_vars["prop_bone"].get()
            target_str = self._prop_vars["prop_target"].get().upper()
            time_val = float(self._prop_vars["prop_time"].get() or 0.0)
            x = float(self._prop_vars["prop_x"].get() or 0.0)
            y = float(self._prop_vars["prop_y"].get() or 0.0)
            z = float(self._prop_vars["prop_z"].get() or 0.0)
            w = float(self._prop_vars["prop_w"].get() or 1.0)
            interp_str = self._prop_vars["prop_interp"].get().upper()

            target = (
                ChannelTarget[target_str]
                if target_str in ChannelTarget.__members__
                else ChannelTarget.ROTATION
            )
            interp = (
                KeyframeType[interp_str]
                if interp_str in KeyframeType.__members__
                else KeyframeType.LINEAR
            )

            if target == ChannelTarget.ROTATION:
                value = [x, y, z, w]
            elif target == ChannelTarget.WEIGHT:
                value = x
            else:
                value = [x, y, z]

            self.active_clip.add_keyframe(bone, target, time_val, value, interp)
            self._redraw_timeline()
            self._redraw_viewport()
            self._mark_dirty()
            self.status_var.set(f"Keyframe applied: {bone} {target.name} @ {time_val:.3f}s")
        except (ValueError, KeyError) as exc:
            messagebox.showwarning("Properties Error", str(exc))

    # -----------------------------------------------------------------------
    # Document editing (Edit menu)
    # -----------------------------------------------------------------------

    def _add_clip(self) -> None:
        """Prompt for a new clip name and create it."""
        dialog = _SimpleDialog(self.root, title="New Clip", prompt="Clip name:")
        name = dialog.result
        if name:
            clip = AnimationClip(name.strip())
            self.clips.append(clip)
            self.active_clip = clip
            self.loop_var.set(bool(clip.loop))
            self._mark_dirty()
            self._refresh_ui()

    def _rename_clip(self) -> None:
        """Prompt for a new name and rename the active clip."""
        if not self.active_clip:
            messagebox.showinfo("Rename Clip", "No active clip to rename.")
            return
        dialog = _SimpleDialog(
            self.root,
            title="Rename Clip",
            prompt="New clip name:",
            initial=self.active_clip.name,
        )
        new_name = dialog.result
        if not new_name:
            return
        new_name = new_name.strip()
        if new_name == self.active_clip.name:
            return
        existing_names = [c.name for c in self.clips if c is not self.active_clip]
        if is_rename_collision(new_name, existing_names):
            messagebox.showwarning("Rename Clip", f"A clip named '{new_name}' already exists.")
            return
        old_name = self.active_clip.name
        self.active_clip.name = new_name
        if old_name in self._baseline_clip_snapshots:
            self._baseline_clip_snapshots[new_name] = self._baseline_clip_snapshots.pop(old_name)
        self._mark_dirty()
        self._refresh_ui()

    def _duplicate_clip(self) -> None:
        """Create a copy of the active clip with a unique name."""
        if not self.active_clip:
            messagebox.showinfo("Duplicate Clip", "No active clip to duplicate.")
            return
        existing_names = {c.name for c in self.clips}
        base = self.active_clip.name
        candidate = unique_duplicate_name(base, existing_names)
        new_clip = AnimationClip.from_dict(deepcopy(self.active_clip.to_dict()))
        new_clip.name = candidate
        self.clips.append(new_clip)
        self.active_clip = new_clip
        self.loop_var.set(bool(new_clip.loop))
        self._mark_dirty()
        self._refresh_ui()
        self.status_var.set(f"Duplicated clip as '{candidate}'")

    def _delete_clip(self) -> None:
        """Remove the active clip from the document."""
        if not self.active_clip:
            messagebox.showinfo("Delete Clip", "No active clip to delete.")
            return
        if len(self.clips) <= 1:
            messagebox.showwarning(
                "Delete Clip", "Cannot delete the last clip. A document must have at least one clip."
            )
            return
        confirmed = messagebox.askyesno(
            "Delete Clip",
            f"Permanently delete clip '{self.active_clip.name}'?",
        )
        if not confirmed:
            return
        deleted_name = self.active_clip.name
        self.clips.remove(self.active_clip)
        self._baseline_clip_snapshots.pop(deleted_name, None)
        self.active_clip = self.clips[0]
        self.loop_var.set(bool(self.active_clip.loop))
        self._mark_dirty()
        self._refresh_ui()

    def _on_clip_list_right_click(self, event) -> None:
        """Show context menu on right-click in the clip browser."""
        if self.clip_listbox.size() > 0:
            idx = self.clip_listbox.nearest(event.y)
            if 0 <= idx < self.clip_listbox.size():
                self.clip_listbox.selection_clear(0, tk.END)
                self.clip_listbox.selection_set(idx)
                self._on_clip_list_selected()
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Rename…", command=self._rename_clip)
        menu.add_command(label="Duplicate", command=self._duplicate_clip)
        menu.add_separator()
        menu.add_command(label="Delete", command=self._delete_clip)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _generate_from_profile(self) -> None:
        """Generate all required clips for a selected style profile using the procedural backend."""
        from animation_engine.backend import BackendRegistry
        from animation_engine.integration import get_style_profile, list_style_profiles

        if not self.model or not self.model.skeleton:
            messagebox.showwarning(
                "Generate from Profile",
                "A skeleton is required. Create or open a document with a skeleton first.",
            )
            return

        profiles = list_style_profiles()
        profile_ids = [p.profile_id for p in profiles]
        if not profile_ids:
            messagebox.showwarning("Generate from Profile", "No style profiles available.")
            return

        # Ask user to pick a profile
        dlg = _ChoiceDialog(
            self.root,
            title="Generate Clips from Profile",
            prompt="Select a style profile:",
            choices=profile_ids,
        )
        chosen = dlg.result
        if not chosen:
            return

        profile = get_style_profile(chosen)
        backend = BackendRegistry.get("procedural")
        skeleton = self.model.skeleton

        existing_names = {c.name for c in self.clips}
        added = 0
        skipped = 0
        failed: list[str] = []
        for spec in profile.required_clips:
            if spec.motion_type in existing_names:
                skipped += 1
                continue
            try:
                clip = backend.generate_clip(
                    skeleton,
                    spec.motion_type,
                    spec.duration,
                    cadence_scale=profile.cadence_scale,
                    amplitude_scale=profile.amplitude_scale,
                )
                clip.loop = spec.motion_type.endswith("_loop") or spec.motion_type in {
                    "idle", "idle_alt", "idle_combat", "walk", "run", "sprint",
                    "crouch_walk", "guard_walk", "swim_idle", "swim_forward",
                    "ladder_up", "ladder_down", "climb_loop",
                    "block", "cast_channel",
                }
                self.clips.append(clip)
                existing_names.add(clip.name)
                added += 1
            except Exception as exc:
                failed.append(spec.motion_type)
                self.status_var.set(f"Warning: failed generating '{spec.motion_type}': {exc}")

        if added > 0:
            self.active_clip = self.clips[-added]
            self.loop_var.set(bool(self.active_clip.loop))
            self._mark_dirty()
            self._refresh_ui()
        msg = f"Generated {added} clip(s) from profile '{chosen}'."
        if skipped:
            msg += f" Skipped {skipped} existing clip(s)."
        if failed:
            msg += f" {len(failed)} clip(s) failed: {', '.join(failed)}."
        self.status_var.set(msg)
        messagebox.showinfo("Generate from Profile", msg)

    def _add_bone(self) -> None:
        """Prompt for a bone name and add it to the skeleton."""
        if not self.model:
            return
        if not self.model.skeleton:
            self.model.skeleton = Skeleton("Character")
        dialog = _SimpleDialog(self.root, title="Add Bone", prompt="Bone name:")
        name = dialog.result
        if name:
            selected = self.bone_tree.focus()
            parent_idx = self.model.skeleton.get_bone_index(selected)
            self.model.skeleton.add_bone(name.strip(), parent_index=parent_idx)
            self.model.skeleton.compute_bind_pose()
            self._mark_dirty()
            self._refresh_ui()

    def _rename_bone(self) -> None:
        """Prompt for a new name and rename the selected bone."""
        if not self.model or not self.model.skeleton:
            return
        selected = self.bone_tree.focus()
        if not selected:
            messagebox.showinfo("Rename Bone", "No bone selected.")
            return
        dialog = _SimpleDialog(
            self.root,
            title="Rename Bone",
            prompt="New bone name:",
            initial=selected,
        )
        new_name = dialog.result
        if not new_name:
            return
        new_name = new_name.strip()
        if new_name == selected:
            return
        if not self.model.skeleton.rename_bone(selected, new_name):
            messagebox.showwarning(
                "Rename Bone",
                f"Cannot rename '{selected}': name '{new_name}' is already taken or bone not found.",
            )
            return
        # Update all animation channels in every clip that reference the old name
        for clip in self.clips:
            clip.rename_bone_channels(selected, new_name)
        self.model.skeleton.compute_bind_pose()
        self._mark_dirty()
        self._refresh_ui()
        self.status_var.set(f"Bone '{selected}' renamed to '{new_name}'.")

    def _delete_bone(self) -> None:
        """Delete the selected leaf bone from the skeleton."""
        if not self.model or not self.model.skeleton:
            return
        selected = self.bone_tree.focus()
        if not selected:
            messagebox.showinfo("Delete Bone", "No bone selected.")
            return
        bone = self.model.skeleton.get_bone(selected)
        if bone is None:
            return
        if bone.children:
            messagebox.showwarning(
                "Delete Bone",
                f"Cannot delete '{selected}': it has child bones.\n"
                "Delete all children first.",
            )
            return
        confirmed = messagebox.askyesno(
            "Delete Bone",
            f"Permanently delete bone '{selected}' and its animation channels?",
        )
        if not confirmed:
            return
        # Remove animation channels for this bone from all clips
        for clip in self.clips:
            clip.remove_bone_channels(selected)
        self.model.skeleton.remove_bone(selected)
        self.model.skeleton.compute_bind_pose()
        self._mark_dirty()
        self._refresh_ui()
        self.status_var.set(f"Bone '{selected}' deleted.")

    def _on_bone_tree_right_click(self, event) -> None:
        """Show context menu on right-click in the bone tree."""
        item = self.bone_tree.identify_row(event.y)
        if item:
            self.bone_tree.selection_set(item)
            self.bone_tree.focus(item)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Add Child Bone…", command=self._add_bone)
        menu.add_command(label="Rename Bone…", command=self._rename_bone)
        menu.add_separator()
        menu.add_command(label="Delete Bone", command=self._delete_bone)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _add_event(self) -> None:
        """Add a timeline event marker to the active clip."""
        if not self.active_clip:
            messagebox.showinfo("Add Event", "No active clip selected.")
            return
        ev_name = self._ev_name_var.get().strip()
        if not ev_name:
            messagebox.showwarning("Add Event", "Enter an event name.")
            return
        try:
            ev_time = float(self._ev_time_var.get() or self.playback.time_seconds)
        except ValueError:
            ev_time = self.playback.time_seconds
        self.active_clip.add_event(ev_name, ev_time)
        self._refresh_event_list()
        self._redraw_timeline()
        self._redraw_viewport()
        self._mark_dirty()
        self.status_var.set(f"Event '{ev_name}' added at t={ev_time:.3f}s")

    def _remove_selected_event(self) -> None:
        """Remove the selected event from the active clip."""
        if not self.active_clip:
            return
        sel = self._event_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.active_clip.remove_event_at_index(idx)
        self._refresh_event_list()
        self._redraw_timeline()
        self._redraw_viewport()
        self._mark_dirty()

    def _refresh_event_list(self) -> None:
        """Sync the event listbox with the active clip's events."""
        self._event_listbox.delete(0, tk.END)
        if not self.active_clip:
            return
        for ev in self.active_clip.get_events():
            self._event_listbox.insert(tk.END, f"{ev['time']:.3f}s  {ev['name']}")

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def _on_clip_selected(self, event=None) -> None:
        name = self.clip_var.get()
        for clip in self.clips:
            if clip.name == name:
                self.active_clip = clip
                self.loop_var.set(bool(clip.loop))
                names = [c.name for c in self.clips]
                if clip.name in names:
                    idx = names.index(clip.name)
                    self.clip_listbox.selection_clear(0, tk.END)
                    self.clip_listbox.selection_set(idx)
                self._refresh_event_list()
                self._sync_playback_controls()
                self._redraw_timeline()
                self._redraw_viewport()
                break

    def _on_bone_selected(self, event=None) -> None:
        """Populate the properties panel for the selected bone."""
        selected = self.bone_tree.focus()
        self._prop_vars["prop_bone"].set(selected)
        self._prop_vars["prop_target"].set("ROTATION")
        self._prop_vars["prop_time"].set(f"{self.playback.time_seconds:.3f}")
        self._prop_vars["prop_x"].set("0.0")
        self._prop_vars["prop_y"].set("0.0")
        self._prop_vars["prop_z"].set("0.0")
        self._prop_vars["prop_w"].set("1.0")
        self._prop_vars["prop_interp"].set("LINEAR")

    def _on_timeline_click(self, event) -> None:
        """Move the playhead to the clicked position."""
        x = self.timeline_canvas.canvasx(event.x)
        t = (x - HEADER_WIDTH) / TIMELINE_PX_PER_SEC
        self.playback.scrub(max(0.0, t), self._active_duration())
        self.time_var.set(f"{self.playback.time_seconds:.3f} s")
        self.scrub_scale.set(self.playback.time_seconds)
        self._redraw_timeline()
        self._redraw_viewport()

    def _on_clip_list_selected(self, event=None) -> None:
        sel = self.clip_listbox.curselection()
        if not sel:
            return
        clip_name = self.clip_listbox.get(sel[0])
        self.clip_var.set(clip_name)
        self._on_clip_selected()

    def _on_scrub_changed(self, value: str) -> None:
        self.playback.scrub(float(value), self._active_duration())
        self.time_var.set(f"{self.playback.time_seconds:.3f} s")
        self._redraw_timeline()
        self._redraw_viewport()

    def _on_loop_toggled(self) -> None:
        if self.active_clip:
            self.active_clip.loop = bool(self.loop_var.get())
            self._mark_dirty()

    # -----------------------------------------------------------------------
    # Session helpers
    # -----------------------------------------------------------------------

    def _active_duration(self) -> float:
        if self.active_clip and self.active_clip.duration > 0.0:
            return self.active_clip.duration
        return TIMELINE_SECONDS

    def _active_loop(self) -> bool:
        return bool(self.loop_var.get())

    def _sync_playback_controls(self) -> None:
        try:
            self.playback.speed = float(self.playback_speed_var.get())
        except ValueError:
            self.playback.speed = 1.0
            self.playback_speed_var.set("1.0")
        max_t = self._active_duration()
        self.scrub_scale.configure(to=max_t)
        self.playback.scrub(self.playback.time_seconds, max_t)
        self.time_var.set(f"{self.playback.time_seconds:.3f} s")
        self.scrub_scale.set(self.playback.time_seconds)

    def _mark_dirty(self) -> None:
        self._is_dirty = True
        self._update_title()

    def _update_title(self) -> None:
        if self._current_file:
            label = os.path.basename(self._current_file)
        else:
            label = "New Document"
        dirty = " *" if self._is_dirty else ""
        self.root.title(f"{APP_TITLE} — {label}{dirty}")

    def _confirm_discard_unsaved(self, action_label: str) -> bool:
        if not self._is_dirty:
            return True
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            f"{action_label}\n\nSave current changes first?",
        )
        if result is None:
            return False
        if result:
            self._save_file()
            return not self._is_dirty
        return True

    def _on_exit_requested(self) -> None:
        if self._confirm_discard_unsaved("Exit editor?"):
            self.root.quit()

    def _remember_recent_file(self, path: str) -> None:
        self._recent_files = merge_recent_files(self._recent_files, path, RECENT_FILES_LIMIT)
        self._rebuild_recent_files_menu()

    def _rebuild_recent_files_menu(self) -> None:
        if self._recent_menu is None:
            return
        self._recent_menu.delete(0, tk.END)
        if not self._recent_files:
            self._recent_menu.add_command(label="(empty)", state=tk.DISABLED)
            return
        for path in self._recent_files:
            self._recent_menu.add_command(
                label=path,
                command=lambda p=path: self._open_recent_file(p),
            )

    def _open_recent_file(self, path: str) -> None:
        if not self._confirm_discard_unsaved("Open recent file?"):
            return
        if not os.path.exists(path):
            messagebox.showwarning("Recent Files", f"File not found:\n{path}")
            return
        try:
            importer = AnimImporter()
            model, clips, morph_tracks, metadata = importer.import_file(path, include_metadata=True)
            self.model = model
            self.clips = clips
            self.morph_tracks = morph_tracks
            self.active_clip = clips[0] if clips else None
            self._current_file = normalize_path(path)
            self._document_metadata = metadata or {}
            self._baseline_clip_snapshots = {clip.name: deepcopy(clip.to_dict()) for clip in clips}
            self._apply_editor_metadata()
            self._is_dirty = False
            self._remember_recent_file(path)
            self._update_title()
            self._refresh_ui()
            self.status_var.set(f"Opened: {path}")
        except Exception as exc:
            messagebox.showerror("Open Error", str(exc))

    def _build_export_metadata(self) -> dict:
        metadata = (
            deepcopy(self._document_metadata) if isinstance(self._document_metadata, dict) else {}
        )
        metadata["editor_state"] = {
            "selected_clip": self.active_clip.name if self.active_clip else "",
            "playback_time": self.playback.time_seconds,
            "playback_speed": self.playback.speed,
            "loop": bool(self.loop_var.get()),
            "viewer": {
                "lighting": self.viewer_lighting_var.get(),
                "show_grid": bool(self.viewer_grid_var.get()),
                "compare": bool(self.compare_var.get()),
                "camera_yaw": self._camera_yaw,
                "camera_pitch": self._camera_pitch,
                "camera_distance": self._camera_distance,
                "camera_pan": self._camera_pan.to_list(),
            },
        }
        self._document_metadata = metadata
        return metadata

    def _apply_editor_metadata(self) -> None:
        state = {}
        if isinstance(self._document_metadata, dict):
            state = self._document_metadata.get("editor_state") or {}
        if not isinstance(state, dict):
            state = {}
        selected_clip = state.get("selected_clip", "")
        if selected_clip:
            for clip in self.clips:
                if clip.name == selected_clip:
                    self.active_clip = clip
                    break
        self.playback.scrub(float(state.get("playback_time", 0.0)), self._active_duration())
        self.playback.speed = float(state.get("playback_speed", 1.0))
        self.playback_speed_var.set(f"{self.playback.speed:.2f}".rstrip("0").rstrip("."))
        self.loop_var.set(
            bool(state.get("loop", self.active_clip.loop if self.active_clip else True))
        )
        if self.active_clip:
            self.active_clip.loop = bool(self.loop_var.get())
        viewer = state.get("viewer") if isinstance(state.get("viewer"), dict) else {}
        if viewer:
            self.viewer_lighting_var.set(viewer.get("lighting", self.viewer_lighting_var.get()))
            self.viewer_grid_var.set(bool(viewer.get("show_grid", self.viewer_grid_var.get())))
            self.compare_var.set(bool(viewer.get("compare", self.compare_var.get())))
            self._camera_yaw = float(viewer.get("camera_yaw", self._camera_yaw))
            self._camera_pitch = float(viewer.get("camera_pitch", self._camera_pitch))
            self._camera_distance = float(viewer.get("camera_distance", self._camera_distance))
            camera_pan = viewer.get("camera_pan", self._camera_pan.to_list())
            if isinstance(camera_pan, list) and len(camera_pan) >= 3:
                self._camera_pan = Vector3.from_list(camera_pan)

    # -----------------------------------------------------------------------
    # PS2-style viewport preview
    # -----------------------------------------------------------------------

    def _on_viewport_drag_start(self, event) -> None:
        self._is_panning_view = bool(event.state & 0x0001)
        self._last_view_drag = (event.x, event.y)

    def _on_viewport_orbit_drag(self, event) -> None:
        if self._is_panning_view:
            return
        if not self._last_view_drag:
            self._last_view_drag = (event.x, event.y)
            return
        dx = event.x - self._last_view_drag[0]
        dy = event.y - self._last_view_drag[1]
        self._camera_yaw += dx * 0.01
        self._camera_pitch = max(-1.25, min(1.25, self._camera_pitch + dy * 0.01))
        self._last_view_drag = (event.x, event.y)
        self._redraw_viewport()

    def _on_viewport_pan_drag(self, event) -> None:
        if not self._last_view_drag:
            self._last_view_drag = (event.x, event.y)
            return
        dx = event.x - self._last_view_drag[0]
        dy = event.y - self._last_view_drag[1]
        self._camera_pan = self._camera_pan + Vector3(-dx * 0.01, dy * 0.01, 0.0)
        self._last_view_drag = (event.x, event.y)
        self._redraw_viewport()

    def _on_viewport_drag_end(self, _event) -> None:
        self._last_view_drag = None
        self._is_panning_view = False

    def _on_viewport_zoom(self, event) -> None:
        delta = 1 if event.delta > 0 else -1
        self._camera_distance = max(1.2, min(20.0, self._camera_distance - delta * 0.4))
        self._redraw_viewport()

    def _redraw_viewport(self) -> None:
        if not hasattr(self, "viewport_canvas"):
            return
        c = self.viewport_canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        preset = PS2_LIGHTING_PRESETS.get(
            self.viewer_lighting_var.get(), PS2_LIGHTING_PRESETS["ps2_studio"]
        )
        c.create_rectangle(0, 0, w, h, fill="#131821", outline="")
        if self.viewer_grid_var.get():
            self._draw_view_grid(c, w, h, preset["grid"])
        if not self.model or not self.model.skeleton:
            c.create_text(
                w // 2,
                h // 2,
                text="Load or create a clip to preview PS2-style motion",
                fill="#7f8da0",
            )
            return
        primary_world = self._evaluate_pose_world_matrices(
            self.active_clip, self.playback.time_seconds
        )
        self._draw_skeleton_world(
            c, w, h, self.model.skeleton, primary_world, preset["skeleton"], preset["joint"]
        )
        self._draw_mesh_wireframe(c, w, h, primary_world, preset)
        if self.compare_var.get():
            baseline = self._baseline_clip_snapshots.get(
                self.active_clip.name if self.active_clip else ""
            )
            if baseline:
                compare_clip = AnimationClip.from_dict(deepcopy(baseline))
                compare_world = self._evaluate_pose_world_matrices(
                    compare_clip, self.playback.time_seconds
                )
                self._draw_skeleton_world(
                    c,
                    w,
                    h,
                    self.model.skeleton,
                    compare_world,
                    "#7ec0ff",
                    "#b8ddff",
                    world_offset=Vector3(1.2, 0.0, 0.0),
                    dashed=True,
                )
        c.create_text(
            10,
            10,
            text=f"{self.viewer_lighting_var.get()}  |  drag=orbit shift+drag=pan wheel=zoom",
            anchor="nw",
            fill="#93a6c2",
            font=("Helvetica", 8),
        )

    def _draw_mesh_wireframe(
        self,
        canvas: tk.Canvas,
        width: int,
        height: int,
        world_mats: list,
        preset: Dict[str, str],
    ) -> None:
        """Draw a PS2-style wireframe overlay for all model meshes (Task 23)."""
        if not self.model or not self.model.meshes or not self.model.skeleton:
            return
        skel = self.model.skeleton
        skin_mats = [
            world_mats[i] * skel.bones[i].inverse_bind
            for i in range(min(len(world_mats), len(skel.bones)))
        ]
        if not skin_mats:
            return
        wire_color = preset.get("wire", preset.get("grid", "#2a4a6a"))
        for mesh in self.model.meshes:
            if not mesh.vertices or not mesh.indices:
                continue
            skinned_mesh = cpu_skin_mesh(mesh, skin_mats)
            verts = mesh.vertices
            skinned_verts = skinned_mesh.vertices
            cached_pts: Dict[int, Optional[tuple[float, float]]] = {}
            for vi, v in enumerate(verts):
                if not any(
                    wi < len(v.bone_weights)
                    and v.bone_weights[wi] > 1e-6
                    and 0 <= bi < len(skin_mats)
                    for wi, bi in enumerate(v.bone_indices)
                ):
                    cached_pts[vi] = None
                    continue
                pos = skinned_verts[vi].position
                cached_pts[vi] = self._project_world_point(pos, width, height)
            # Draw triangle edges (de-duplicate shared edges for speed).
            drawn_edges: set = set()
            for i in range(0, len(mesh.indices), 3):
                i0, i1, i2 = mesh.indices[i], mesh.indices[i + 1], mesh.indices[i + 2]
                for a, b in ((i0, i1), (i1, i2), (i2, i0)):
                    edge = (min(a, b), max(a, b))
                    if edge in drawn_edges:
                        continue
                    drawn_edges.add(edge)
                    pa, pb = cached_pts.get(a), cached_pts.get(b)
                    if pa and pb:
                        canvas.create_line(
                            pa[0], pa[1], pb[0], pb[1],
                            fill=wire_color, width=1,
                        )

    def _draw_view_grid(self, canvas: tk.Canvas, width: int, height: int, color: str) -> None:
        for x in range(0, width, 40):
            canvas.create_line(x, 0, x, height, fill=color, width=1)
        for y in range(0, height, 40):
            canvas.create_line(0, y, width, y, fill=color, width=1)

    def _evaluate_pose_world_matrices(
        self, clip: Optional[AnimationClip], time_seconds: float
    ) -> list[Matrix4x4]:
        if not self.model or not self.model.skeleton:
            return []
        skel = self.model.skeleton
        local_pose: list[Transform] = []
        for bone in skel.bones:
            base = bone.local_transform
            if clip is None:
                local_pose.append(base)
                continue
            sample_time = time_seconds
            duration = clip.duration
            if clip.loop and duration > 1e-6:
                sample_time = time_seconds % duration
            t_ch = clip.get_channel(bone.name, ChannelTarget.TRANSLATION)
            r_ch = clip.get_channel(bone.name, ChannelTarget.ROTATION)
            s_ch = clip.get_channel(bone.name, ChannelTarget.SCALE)
            translation = Vector3.from_list(t_ch.evaluate(sample_time)) if t_ch else base.position
            rotation = Quaternion.from_list(r_ch.evaluate(sample_time)) if r_ch else base.rotation
            scale = Vector3.from_list(s_ch.evaluate(sample_time)) if s_ch else base.scale
            local_pose.append(Transform(translation, rotation, scale))
        return skel.get_world_matrices(local_pose)

    def _draw_skeleton_world(
        self,
        canvas: tk.Canvas,
        width: int,
        height: int,
        skeleton: Skeleton,
        world_mats: list[Matrix4x4],
        line_color: str,
        joint_color: str,
        world_offset: Optional[Vector3] = None,
        dashed: bool = False,
    ) -> None:
        if not world_mats:
            return
        projected_points: Dict[int, tuple[float, float]] = {}
        for bone in skeleton.bones:
            pos = world_mats[bone.index].transform_point(Vector3.zero())
            if world_offset is not None:
                pos = pos + world_offset
            pt = self._project_world_point(pos, width, height)
            if pt:
                projected_points[bone.index] = pt
        for bone in skeleton.bones:
            parent = bone.parent_index
            if parent < 0 or bone.index not in projected_points or parent not in projected_points:
                continue
            x0, y0 = projected_points[parent]
            x1, y1 = projected_points[bone.index]
            canvas.create_line(
                x0,
                y0,
                x1,
                y1,
                fill=line_color,
                width=2,
                dash=(4, 3) if dashed else None,
            )
        for _, (x, y) in projected_points.items():
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=joint_color, outline="")

    def _project_world_point(
        self, point: Vector3, width: int, height: int
    ) -> Optional[tuple[float, float]]:
        target = self._camera_pan
        eye = Vector3(
            target.x
            + self._camera_distance * math.cos(self._camera_pitch) * math.sin(self._camera_yaw),
            target.y + self._camera_distance * math.sin(self._camera_pitch),
            target.z
            + self._camera_distance * math.cos(self._camera_pitch) * math.cos(self._camera_yaw),
        )
        view = Matrix4x4.look_at(eye, target, Vector3.up())
        proj = Matrix4x4.perspective(1.1, max(0.1, width / max(1, height)), 0.1, 100.0)
        clip_v = proj.transform_vector4(view.transform_vector4(Vector4.from_vector3(point, 1.0)))
        if abs(clip_v.w) < 1e-6:
            return None
        ndc_x = clip_v.x / clip_v.w
        ndc_y = clip_v.y / clip_v.w
        if not (-2.0 <= ndc_x <= 2.0 and -2.0 <= ndc_y <= 2.0):
            return None
        sx = (ndc_x * 0.5 + 0.5) * width
        sy = (1.0 - (ndc_y * 0.5 + 0.5)) * height
        return sx, sy

    # -----------------------------------------------------------------------
    # Misc
    # -----------------------------------------------------------------------

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About Animation Engine",
            "Animation Engine v1.0\n\n"
            "A professional animation tool for Game Engine for Teaching.\n"
            "Inspired by Final Fantasy 15's animation pipeline.\n\n"
            "Supports:\n"
            "  • Skeletal animation (50+ bones)\n"
            "  • Cubic-spline keyframe interpolation\n"
            "  • Animation blending & state machine\n"
            "  • Inverse Kinematics (FABRIK)\n"
            "  • Blend-shape / morph-target animation\n"
            "  • PBR material authoring\n"
            "  • Export: .anim (JSON) and glTF 2.0",
        )

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Simple dialog helper
# ---------------------------------------------------------------------------


class _SimpleDialog(tk.Toplevel):
    """Minimal single-field text dialog."""

    def __init__(self, parent, title: str, prompt: str, initial: str = "") -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        tk.Label(self, text=prompt, padx=10, pady=6).pack()
        self._entry = tk.Entry(self, width=30)
        self._entry.pack(padx=10, pady=4)
        if initial:
            self._entry.insert(0, initial)
            self._entry.select_range(0, tk.END)
        self._entry.focus_set()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="OK", width=8, command=self._ok).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Cancel", width=8, command=self.destroy).pack(
            side=tk.LEFT, padx=4
        )
        self.bind("<Return>", lambda _: self._ok())
        self.wait_window()

    def _ok(self) -> None:
        self.result = self._entry.get()
        self.destroy()


class _ChoiceDialog(tk.Toplevel):
    """Dropdown selection dialog."""

    def __init__(self, parent, title: str, prompt: str, choices: list[str]) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        tk.Label(self, text=prompt, padx=10, pady=6).pack()
        self._var = tk.StringVar(value=choices[0] if choices else "")
        combo = ttk.Combobox(self, textvariable=self._var, values=choices, state="readonly", width=28)
        combo.pack(padx=10, pady=4)
        combo.focus_set()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="OK", width=8, command=self._ok).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Cancel", width=8, command=self.destroy).pack(
            side=tk.LEFT, padx=4
        )
        self.bind("<Return>", lambda _: self._ok())
        self.wait_window()

    def _ok(self) -> None:
        self.result = self._var.get()
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Launch the Animation Editor."""
    editor = AnimationEditor()
    editor.run()


if __name__ == "__main__":
    main()
