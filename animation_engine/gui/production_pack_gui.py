"""Tkinter GUI for production pack generation and validation."""

from __future__ import annotations

import io
import threading
import tkinter as tk
from contextlib import redirect_stdout
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from animation_engine.cli import build_parser, _cmd_generate_pack, _cmd_validate_pack
from animation_engine.integration.style_profiles import list_style_profiles


class ProductionPackGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Animation Engine — Production Pack Builder")
        self.root.geometry("980x680")
        self.root.minsize(860, 560)
        self._is_running = False

        self.skeleton_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.manifest_out_var = tk.StringVar()
        self.json_report_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="procedural")
        self.sample_rate_var = tk.StringVar(value="30.0")
        self.seed_var = tk.StringVar()
        self.strict_var = tk.BooleanVar(value=True)
        self.profile_var = tk.StringVar(
            value=next((profile.profile_id for profile in list_style_profiles()), "ff10_ps2")
        )
        self.status_var = tk.StringVar(value="Ready")

        self._build()

    def _build(self) -> None:
        container = tk.Frame(self.root, padx=10, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        self._add_path_row(
            container,
            "Skeleton .anim",
            self.skeleton_path_var,
            browse=lambda: self._pick_file(self.skeleton_path_var, [("Animation Files", "*.anim")]),
        )
        self._add_path_row(
            container,
            "Output Directory",
            self.output_dir_var,
            browse=lambda: self._pick_dir(self.output_dir_var),
        )
        self._add_path_row(
            container,
            "Manifest Output (optional)",
            self.manifest_out_var,
            browse=lambda: self._pick_save_file(
                self.manifest_out_var, [("JSON Files", "*.json")], "pack_manifest.json"
            ),
        )
        self._add_path_row(
            container,
            "Validation Report (optional)",
            self.json_report_var,
            browse=lambda: self._pick_save_file(
                self.json_report_var, [("JSON Files", "*.json")], "validation_report.json"
            ),
        )

        options = tk.Frame(container)
        options.pack(fill=tk.X, pady=(8, 8))

        tk.Label(options, text="Profile").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        profiles = [profile.profile_id for profile in list_style_profiles()]
        profile_combo = ttk.Combobox(
            options,
            textvariable=self.profile_var,
            state="readonly",
            values=profiles,
            width=16,
        )
        profile_combo.grid(row=0, column=1, sticky="w", pady=4)

        tk.Label(options, text="Backend").grid(row=0, column=2, sticky="w", padx=(16, 6), pady=4)
        backend_combo = ttk.Combobox(
            options,
            textvariable=self.backend_var,
            state="readonly",
            values=["procedural"],
            width=16,
        )
        backend_combo.grid(row=0, column=3, sticky="w", pady=4)

        tk.Label(options, text="Sample Rate").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        tk.Entry(options, textvariable=self.sample_rate_var, width=19).grid(
            row=1, column=1, sticky="w", pady=4
        )

        tk.Label(options, text="Seed (optional)").grid(
            row=1, column=2, sticky="w", padx=(16, 6), pady=4
        )
        tk.Entry(options, textvariable=self.seed_var, width=19).grid(
            row=1, column=3, sticky="w", pady=4
        )

        tk.Checkbutton(
            options,
            text="Strict mode (fail if any clip generation fails)",
            variable=self.strict_var,
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        action_row = tk.Frame(container)
        action_row.pack(fill=tk.X, pady=(4, 6))
        self.run_button = tk.Button(
            action_row, text="Generate + Validate Full Production Pack", command=self._run_pipeline
        )
        self.run_button.pack(side=tk.LEFT)
        tk.Label(action_row, textvariable=self.status_var).pack(side=tk.LEFT, padx=12)

        tk.Label(container, text="Log Output").pack(anchor="w")
        self.log_text = tk.Text(container, wrap="word")
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _add_path_row(self, parent: tk.Widget, label: str, variable: tk.StringVar, browse) -> None:
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        tk.Label(row, text=label, width=28, anchor="w").pack(side=tk.LEFT)
        tk.Entry(row, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row, text="Browse...", command=browse).pack(side=tk.LEFT)

    def _pick_file(self, variable: tk.StringVar, types: list[tuple[str, str]]) -> None:
        path = filedialog.askopenfilename(filetypes=types)
        if path:
            variable.set(path)

    def _pick_dir(self, variable: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            variable.set(path)

    def _pick_save_file(
        self, variable: tk.StringVar, types: list[tuple[str, str]], default_name: str
    ) -> None:
        path = filedialog.asksaveasfilename(
            filetypes=types,
            defaultextension=".json",
            initialfile=default_name,
        )
        if path:
            variable.set(path)

    def _run_pipeline(self) -> None:
        if self._is_running:
            return
        skeleton_anim = self.skeleton_path_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        if not skeleton_anim or not output_dir:
            messagebox.showerror(
                "Missing Input", "Skeleton .anim and output directory are required."
            )
            return
        if not Path(skeleton_anim).exists():
            messagebox.showerror("Invalid Path", f"Skeleton file does not exist:\n{skeleton_anim}")
            return

        self._is_running = True
        self.run_button.configure(state=tk.DISABLED)
        self.status_var.set("Running...")
        self.log_text.delete("1.0", tk.END)
        snapshot = {
            "skeleton_anim": skeleton_anim,
            "output_dir": output_dir,
            "profile": self.profile_var.get().strip(),
            "backend": self.backend_var.get().strip(),
            "sample_rate": self.sample_rate_var.get().strip(),
            "seed": self.seed_var.get().strip(),
            "manifest_out": self.manifest_out_var.get().strip(),
            "json_report": self.json_report_var.get().strip(),
            "strict": bool(self.strict_var.get()),
        }
        worker = threading.Thread(target=self._run_pipeline_worker, args=(snapshot,), daemon=True)
        worker.start()

    def _run_pipeline_worker(self, snapshot: dict[str, str | bool]) -> None:
        parser = build_parser()
        output_capture = io.StringIO()
        exit_code = 1

        try:
            generate_argv = [
                "generate-pack",
                "--skeleton-anim",
                str(snapshot["skeleton_anim"]),
                "--output-dir",
                str(snapshot["output_dir"]),
                "--profile",
                str(snapshot["profile"]),
                "--backend",
                str(snapshot["backend"]),
                "--sample-rate",
                str(snapshot["sample_rate"]),
            ]
            seed_value = str(snapshot["seed"])
            if seed_value:
                generate_argv.extend(["--seed", seed_value])
            manifest_out = str(snapshot["manifest_out"])
            if manifest_out:
                generate_argv.extend(["--manifest-out", manifest_out])
            if bool(snapshot["strict"]):
                generate_argv.append("--strict")

            with redirect_stdout(output_capture):
                gen_args = parser.parse_args(generate_argv)
                generate_code = _cmd_generate_pack(gen_args)
                if generate_code != 0:
                    exit_code = generate_code
                else:
                    manifest_path = (
                        Path(manifest_out)
                        if manifest_out
                        else Path(str(snapshot["output_dir"])) / "pack_manifest.json"
                    )
                    validate_argv = ["validate-pack", "--manifest", str(manifest_path)]
                    json_report = str(snapshot["json_report"])
                    if json_report:
                        validate_argv.extend(["--json-report", json_report])
                    validate_args = parser.parse_args(validate_argv)
                    exit_code = _cmd_validate_pack(validate_args)
        except Exception as exc:  # pragma: no cover - defensive GUI path
            output_capture.write(f"\nERROR: {exc}\n")
            exit_code = 1

        log_value = output_capture.getvalue()
        self.root.after(0, lambda: self._finish_pipeline(exit_code, log_value))

    def _finish_pipeline(self, exit_code: int, log_value: str) -> None:
        self.log_text.insert(tk.END, log_value)
        self.log_text.see(tk.END)
        if exit_code == 0:
            self.status_var.set("Completed successfully")
            messagebox.showinfo("Success", "Production pack generation and validation succeeded.")
        else:
            self.status_var.set("Failed")
            messagebox.showerror("Failed", "Production build failed. Check the log output.")
        self.run_button.configure(state=tk.NORMAL)
        self._is_running = False

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = ProductionPackGUI()
    app.run()


if __name__ == "__main__":
    main()
