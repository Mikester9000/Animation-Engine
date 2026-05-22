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
from .state import PlaybackState, merge_recent_files, normalize_path, select_clip_name

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
    "ps2_studio": {"grid": "#33506f", "skeleton": "#f5d06a", "joint": "#f8e3a8"},
    "ps2_field": {"grid": "#395539", "skeleton": "#d8d98f", "joint": "#f0efc3"},
    "ps2_night": {"grid": "#2d3550", "skeleton": "#8ab2ff", "joint": "#c7dbff"},
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
        edit_menu.add_command(label="Add Bone", command=self._add_bone)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Playback menu
        pb_menu = tk.Menu(menubar, tearoff=0)
        pb_menu.add_command(
            label="Play / Pause", accelerator="Space", command=self._toggle_playback
        )
        pb_menu.add_command(label="Stop", command=self._stop_playback)
        pb_menu.add_command(label="Go to Start", accelerator="Home", command=self._go_to_start)
        menubar.add_cascade(label="Playback", menu=pb_menu)

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

        self.viewport_canvas = tk.Canvas(parent, bg="#14181f", highlightthickness=0, cursor="fleur")
        self.viewport_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 6))
        self.viewport_canvas.bind("<Configure>", lambda _: self._redraw_viewport())
        self.viewport_canvas.bind("<ButtonPress-1>", self._on_viewport_drag_start)
        self.viewport_canvas.bind("<B1-Motion>", self._on_viewport_orbit_drag)
        self.viewport_canvas.bind("<Shift-B1-Motion>", self._on_viewport_pan_drag)
        self.viewport_canvas.bind("<ButtonRelease-1>", self._on_viewport_drag_end)
        self.viewport_canvas.bind("<MouseWheel>", self._on_viewport_zoom)

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

    def __init__(self, parent, title: str, prompt: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        tk.Label(self, text=prompt, padx=10, pady=6).pack()
        self._entry = tk.Entry(self, width=30)
        self._entry.pack(padx=10, pady=4)
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Launch the Animation Editor."""
    editor = AnimationEditor()
    editor.run()


if __name__ == "__main__":
    main()
