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
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from ..model.model import Model
from ..model.mesh import Mesh, Vertex
from ..model.material import PBRMaterial
from ..model.skeleton import Skeleton
from ..animation.clip import AnimationClip
from ..animation.channel import ChannelTarget
from ..animation.keyframe import KeyframeType
from ..animation.morph_track import MorphTrack
from ..io.anim_format import AnimExporter, AnimImporter
from ..io.gltf import GltfExporter
from ..math_utils import Vector3, Quaternion, Transform


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_TITLE = "Animation Engine — Editor"
TIMELINE_HEIGHT = 180
TIMELINE_SECONDS = 10.0   # Default visible range in seconds
TIMELINE_PX_PER_SEC = 80  # Pixels per second on the timeline
RULER_HEIGHT = 20
HEADER_WIDTH = 150        # Width of the bone-name label column on the timeline
BG_COLOR = "#2b2b2b"
ACCENT_COLOR = "#e8a020"
TEXT_COLOR = "#dddddd"
GRID_COLOR = "#404040"
KF_COLOR = "#f0c040"
PLAYHEAD_COLOR = "#ff4444"


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
        self.playback_time: float = 0.0
        self.is_playing: bool = False
        self._after_id: Optional[str] = None
        self._current_file: Optional[str] = None

        # Build UI
        self._build_menu()
        self._build_layout()

        # New empty document on startup
        self._new_document()

    # -----------------------------------------------------------------------
    # Menu
    # -----------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self._new_document)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self._open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_file)
        file_menu.add_command(label="Save As…", command=self._save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export glTF 2.0…", command=self._export_gltf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add Keyframe", accelerator="K", command=self._add_keyframe)
        edit_menu.add_command(label="Delete Keyframe", accelerator="Delete", command=self._delete_keyframe)
        edit_menu.add_separator()
        edit_menu.add_command(label="Add Clip", command=self._add_clip)
        edit_menu.add_command(label="Add Bone", command=self._add_bone)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Playback menu
        pb_menu = tk.Menu(menubar, tearoff=0)
        pb_menu.add_command(label="Play / Pause", accelerator="Space", command=self._toggle_playback)
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
            self.root, orient=tk.HORIZONTAL,
            sashwidth=4, bg=BG_COLOR, bd=0,
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
            self.root, textvariable=self.status_var,
            bg="#111", fg=TEXT_COLOR, anchor="w", padx=6,
        )
        status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_toolbar(self, parent: tk.Frame) -> None:
        btn_cfg = dict(bg="#333", fg=TEXT_COLOR, relief=tk.FLAT, padx=8, pady=3)

        tk.Button(parent, text="⏮", command=self._go_to_start, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=4)
        self.play_btn = tk.Button(parent, text="▶ Play", command=self._toggle_playback, **btn_cfg)
        self.play_btn.pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(parent, text="⏹", command=self._stop_playback, **btn_cfg).pack(side=tk.LEFT, padx=2, pady=4)

        tk.Label(parent, text="  Time:", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT, padx=4)
        self.time_var = tk.StringVar(value="0.000 s")
        tk.Label(parent, textvariable=self.time_var, bg="#1e1e1e", fg=ACCENT_COLOR, width=9).pack(side=tk.LEFT)

        # Clip selector
        tk.Label(parent, text="  Clip:", bg="#1e1e1e", fg=TEXT_COLOR).pack(side=tk.LEFT, padx=4)
        self.clip_var = tk.StringVar()
        self.clip_combo = ttk.Combobox(
            parent, textvariable=self.clip_var, state="readonly", width=18
        )
        self.clip_combo.pack(side=tk.LEFT, padx=2, pady=4)
        self.clip_combo.bind("<<ComboboxSelected>>", self._on_clip_selected)

    def _build_left_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Skeleton / Bones", bg=BG_COLOR, fg=ACCENT_COLOR,
                 font=("Helvetica", 9, "bold")).pack(fill=tk.X, padx=4, pady=(6, 2))

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

    def _build_centre_panel(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Viewport Preview\n(Connect Game Engine for Teaching\nrenderer for 3-D display)",
            bg="#1a1a1a", fg="#555555",
            justify=tk.CENTER,
        ).pack(expand=True)

    def _build_right_panel(self, parent: tk.Frame) -> None:
        tk.Label(parent, text="Properties", bg=BG_COLOR, fg=ACCENT_COLOR,
                 font=("Helvetica", 9, "bold")).pack(fill=tk.X, padx=4, pady=(6, 2))

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
            tk.Label(row, text=label + ":", bg=BG_COLOR, fg=TEXT_COLOR, width=9, anchor="e").pack(side=tk.LEFT)
            var = tk.StringVar()
            self._prop_vars[attr] = var
            tk.Entry(row, textvariable=var, bg="#333", fg=TEXT_COLOR,
                     insertbackground=TEXT_COLOR, relief=tk.FLAT, width=14).pack(side=tk.LEFT, padx=2)
        # Apply button
        tk.Button(
            parent, text="Apply Keyframe", bg=ACCENT_COLOR, fg="#111",
            relief=tk.FLAT, command=self._apply_keyframe_from_properties,
        ).pack(fill=tk.X, padx=4, pady=6)

        # Material section
        sep = tk.Frame(parent, bg=GRID_COLOR, height=1)
        sep.pack(fill=tk.X, padx=4, pady=4)
        tk.Label(parent, text="Material", bg=BG_COLOR, fg=ACCENT_COLOR,
                 font=("Helvetica", 9, "bold")).pack(fill=tk.X, padx=4)
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
            tk.Label(row, text=label + ":", bg=BG_COLOR, fg=TEXT_COLOR, width=11, anchor="e").pack(side=tk.LEFT)
            var = tk.StringVar(value="0.0")
            self._mat_vars[attr] = var
            tk.Entry(row, textvariable=var, bg="#333", fg=TEXT_COLOR,
                     insertbackground=TEXT_COLOR, relief=tk.FLAT, width=10).pack(side=tk.LEFT, padx=2)

    def _build_timeline(self, parent: tk.Frame) -> None:
        """Build the scrollable timeline strip."""
        tk.Label(parent, text="Timeline", bg="#1e1e1e", fg=ACCENT_COLOR,
                 font=("Helvetica", 9, "bold")).pack(side=tk.TOP, anchor="w", padx=6)

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

        width = c.winfo_width()
        height = c.winfo_height()

        total_px = int(TIMELINE_SECONDS * TIMELINE_PX_PER_SEC)
        c.configure(scrollregion=(0, 0, total_px + HEADER_WIDTH, height))

        # Ruler background
        c.create_rectangle(
            HEADER_WIDTH, 0, total_px + HEADER_WIDTH, RULER_HEIGHT,
            fill="#1a1a1a", outline=""
        )

        # Second tick marks and labels
        for sec in range(int(TIMELINE_SECONDS) + 1):
            x = HEADER_WIDTH + sec * TIMELINE_PX_PER_SEC
            c.create_line(x, 0, x, RULER_HEIGHT, fill=GRID_COLOR)
            c.create_text(x + 2, RULER_HEIGHT // 2, text=f"{sec}s",
                          fill=TEXT_COLOR, anchor="w", font=("Helvetica", 7))

        # Bone rows
        if self.active_clip and self.model and self.model.skeleton:
            bone_names = [b.name for b in self.model.skeleton.bones]
            row_height = max(20, (height - RULER_HEIGHT) // max(1, len(bone_names)))
            for row_idx, bone_name in enumerate(bone_names):
                y_top = RULER_HEIGHT + row_idx * row_height
                # Row background (alternating)
                row_bg = "#252525" if row_idx % 2 == 0 else "#2a2a2a"
                c.create_rectangle(0, y_top, total_px + HEADER_WIDTH, y_top + row_height,
                                   fill=row_bg, outline="")
                # Bone label
                c.create_text(4, y_top + row_height // 2, text=bone_name,
                              fill=TEXT_COLOR, anchor="w", font=("Helvetica", 8))

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
                            kx, ky - r, kx + r, ky, kx, ky + r, kx - r, ky,
                            fill=KF_COLOR, outline="#fff",
                        )

        # Playhead
        px = HEADER_WIDTH + self.playback_time * TIMELINE_PX_PER_SEC
        c.create_line(px, 0, px, height, fill=PLAYHEAD_COLOR, width=2)
        c.create_polygon(px - 6, 0, px + 6, 0, px, 10, fill=PLAYHEAD_COLOR)

    # -----------------------------------------------------------------------
    # Document management
    # -----------------------------------------------------------------------

    def _new_document(self) -> None:
        """Create an empty document with a minimal skeleton."""
        self.model = Model("NewCharacter")

        # Default skeleton: root + spine hierarchy (minimal FF15-like rig)
        skel = Skeleton("Character")
        root_idx = skel.add_bone("root", parent_index=-1)
        pelvis_idx = skel.add_bone(
            "pelvis", parent_index=root_idx,
            local_transform=Transform(position=Vector3(0, 0.9, 0))
        )
        spine_01 = skel.add_bone(
            "spine_01", parent_index=pelvis_idx,
            local_transform=Transform(position=Vector3(0, 0.2, 0))
        )
        skel.add_bone(
            "spine_02", parent_index=spine_01,
            local_transform=Transform(position=Vector3(0, 0.2, 0))
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

        self.root.title(APP_TITLE + " — New Document")
        self._refresh_ui()
        self.status_var.set("New document created.")

    def _refresh_ui(self) -> None:
        """Synchronise all UI widgets with the current document state."""
        # Clip combo
        clip_names = [c.name for c in self.clips]
        self.clip_combo["values"] = clip_names
        if self.active_clip:
            self.clip_var.set(self.active_clip.name)

        # Bone tree
        self.bone_tree.delete(*self.bone_tree.get_children())
        if self.model and self.model.skeleton:
            self._populate_bone_tree("", self.model.skeleton, -1)

        self._redraw_timeline()

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
        path = filedialog.askopenfilename(
            title="Open Animation File",
            filetypes=[("Animation files", "*.anim"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            importer = AnimImporter()
            model, clips, morph_tracks = importer.import_file(path)
            self.model = model
            self.clips = clips
            self.morph_tracks = morph_tracks
            self.active_clip = clips[0] if clips else None
            self._current_file = path
            self.root.title(f"{APP_TITLE} — {os.path.basename(path)}")
            self._refresh_ui()
            self.status_var.set(f"Opened: {path}")
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
            self._write_file(path)
            self._current_file = path
            self.root.title(f"{APP_TITLE} — {os.path.basename(path)}")

    def _write_file(self, path: str) -> None:
        try:
            exporter = AnimExporter()
            exporter.export(self.model, self.clips, self.morph_tracks, path)
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
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        self.is_playing = True
        self.play_btn.config(text="⏸ Pause")
        self._tick()

    def _pause_playback(self) -> None:
        self.is_playing = False
        self.play_btn.config(text="▶ Play")
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _stop_playback(self) -> None:
        self._pause_playback()
        self.playback_time = 0.0
        self.time_var.set("0.000 s")
        self._redraw_timeline()

    def _go_to_start(self) -> None:
        self._stop_playback()

    def _tick(self) -> None:
        """Advance playback by one frame (30 fps target)."""
        if not self.is_playing:
            return
        dt = 1.0 / 30.0
        self.playback_time += dt
        dur = self.active_clip.duration if self.active_clip else TIMELINE_SECONDS
        if dur > 0.0 and self.playback_time > dur:
            self.playback_time = 0.0  # Loop
        self.time_var.set(f"{self.playback_time:.3f} s")
        self._redraw_timeline()
        self._after_id = self.root.after(int(dt * 1000), self._tick)

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
            self.playback_time,
            [0.0, 0.0, 0.0, 1.0],
        )
        self._redraw_timeline()
        self.status_var.set(
            f"Added keyframe on {selected} at t={self.playback_time:.3f}s"
        )

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
                ch.remove_keyframe(self.playback_time)
        self._redraw_timeline()

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

            target = ChannelTarget[target_str] if target_str in ChannelTarget.__members__ else ChannelTarget.ROTATION
            interp = KeyframeType[interp_str] if interp_str in KeyframeType.__members__ else KeyframeType.LINEAR

            if target == ChannelTarget.ROTATION:
                value = [x, y, z, w]
            elif target == ChannelTarget.WEIGHT:
                value = x
            else:
                value = [x, y, z]

            self.active_clip.add_keyframe(bone, target, time_val, value, interp)
            self._redraw_timeline()
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
            self._refresh_ui()

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def _on_clip_selected(self, event=None) -> None:
        name = self.clip_var.get()
        for clip in self.clips:
            if clip.name == name:
                self.active_clip = clip
                self._redraw_timeline()
                break

    def _on_bone_selected(self, event=None) -> None:
        """Populate the properties panel for the selected bone."""
        selected = self.bone_tree.focus()
        self._prop_vars["prop_bone"].set(selected)
        self._prop_vars["prop_target"].set("ROTATION")
        self._prop_vars["prop_time"].set(f"{self.playback_time:.3f}")
        self._prop_vars["prop_x"].set("0.0")
        self._prop_vars["prop_y"].set("0.0")
        self._prop_vars["prop_z"].set("0.0")
        self._prop_vars["prop_w"].set("1.0")
        self._prop_vars["prop_interp"].set("LINEAR")

    def _on_timeline_click(self, event) -> None:
        """Move the playhead to the clicked position."""
        x = self.timeline_canvas.canvasx(event.x)
        t = (x - HEADER_WIDTH) / TIMELINE_PX_PER_SEC
        self.playback_time = max(0.0, min(TIMELINE_SECONDS, t))
        self.time_var.set(f"{self.playback_time:.3f} s")
        self._redraw_timeline()

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
        tk.Button(btn_frame, text="Cancel", width=8, command=self.destroy).pack(side=tk.LEFT, padx=4)
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
