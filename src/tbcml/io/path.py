from __future__ import annotations

import glob
import os
import shutil
import typing

import tbcml
import re


class Path:
    def __init__(self, path: PathStr = "", is_relative: bool = False):
        if isinstance(path, Path):
            path = path.to_str()
        if is_relative:
            self.path = self.get_relative_path(path)
        else:
            self.path = path

    @staticmethod
    def get_asset_file_path(local_path: tbcml.PathStr) -> tbcml.Path:
        return tbcml.Path(is_relative=True).add("assets").add(local_path)

    def copy_object(self) -> Path:
        return Path(self.path)

    @staticmethod
    def get_root() -> Path:
        return Path(os.path.abspath(os.sep))

    def run(self, arg: list[str], display_output: bool = False) -> tbcml.CommandResult:
        cmd_text = [self.path] + arg
        cmd = tbcml.Command(cmd_text)
        return cmd.run(display=display_output)

    @staticmethod
    def get_lib(lib_name: str) -> Path:
        return Path("lib", is_relative=True).add(lib_name)

    def get_relative_path(self, path: str) -> str:
        return os.path.join(self.get_files_folder().path, path)

    def replace(self, old: str, new: str) -> Path:
        return Path(self.path.replace(old, new))

    @staticmethod
    def get_files_folder() -> Path:
        file = Path(os.path.realpath(__file__))
        if file.get_extension() == "pyc":
            path = file.parent().parent().parent().add("files")
        else:
            path = file.parent().parent().add("files")
        return path

    def strip_trailing_slash(self) -> Path:
        return Path(self.path.rstrip(os.sep))

    def strip_leading_slash(self) -> Path:
        return Path(self.path.lstrip(os.sep))

    def open(self):
        if not self.exists():
            self.generate_dirs()
        if os.name == "nt":
            os.startfile(self.path)
        elif os.name == "posix":
            path_str = self.to_str_forwards()
            if self.is_directory():
                path_str += "/"

            cmd = [
                "dbus-send",
                "--session",
                "--dest=org.freedesktop.FileManager1",
                "--type=method_call",
                "/org/freedesktop/FileManager1",
                "org.freedesktop.FileManager1.ShowItems",
                f"array:string:'file://{path_str}'",
                "string:''",
            ]
            tbcml.Command(cmd).run_in_thread()
        elif os.name == "mac":
            tbcml.Command(["open", self.path]).run()
        else:
            raise OSError("Unknown OS")

    def open_file(self):
        if os.name == "nt":
            os.startfile(self.path)
        elif os.name == "posix":
            cmd = ["xdg-open", self.path]
            tbcml.Command(cmd).run_in_thread()
        elif os.name == "mac":
            tbcml.Command(["open", self.path]).run()
        else:
            raise OSError("Unknown OS")

    def to_str(self) -> str:
        return self.path

    def to_str_forwards(self) -> str:
        return self.path.replace("\\", "/")

    @staticmethod
    def get_documents_folder(app_name: str = "tbcml") -> Path:
        os_name = os.name
        if os_name == "nt":
            path = Path.join(os.environ["USERPROFILE"], "Documents", app_name)
        elif os_name == "posix":
            path = Path.join(os.environ["HOME"], "Documents", app_name)
        elif os_name == "mac":
            path = Path.join(os.environ["HOME"], "Documents", app_name)
        else:
            raise OSError("Unknown OS")
        path.generate_dirs()
        return path

    def generate_dirs(self: Path) -> Path:
        if not self.exists():
            try:
                self.__make_dirs()
            except OSError:
                pass
        return self

    def create(self) -> Path:
        if not self.exists():
            self.write(tbcml.Data("test"))
        return self

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def is_file(self) -> bool:
        return os.path.isfile(self.path)

    def __make_dirs(self) -> Path:
        os.makedirs(self.path)
        return self

    def basename(self) -> str:
        return os.path.basename(self.path)

    @staticmethod
    @typing.overload
    def join(*paths: str) -> Path: ...

    @staticmethod
    @typing.overload
    def join(*paths: Path) -> Path: ...

    @staticmethod
    def join(*paths: PathStr) -> Path:
        _paths: list[str] = [str(path) for path in paths]
        return Path(os.path.join(*_paths))

    @typing.overload
    def add(self, *paths: Path) -> Path: ...

    @typing.overload
    def add(self, *paths: str) -> Path: ...

    def add(self, *paths: PathStr) -> Path:
        _paths: list[str] = [str(path) for path in paths]
        return Path(os.path.join(self.path, *_paths))

    def relative_to(self, path: Path) -> Path:
        return Path(os.path.relpath(self.path, path.path))

    def __str__(self) -> str:
        return self.path

    def __repr__(self) -> str:
        return self.path

    def remove_tree(self, ignoreErrors: bool = True) -> Path:
        if self.exists():
            shutil.rmtree(self.path, ignore_errors=ignoreErrors)
        return self

    def remove(self, in_thread: bool = False) -> Path:
        if in_thread:
            return self.remove_thread()
        if self.exists():
            if self.is_directory():
                self.remove_tree()
            else:
                self.remove_file()
        return self

    def remove_file(self):
        os.remove(self.path)

    def remove_thread(self) -> Path:
        if self.exists():
            if self.is_directory():
                tbcml.run_in_thread(self.remove_tree)
            else:
                tbcml.run_in_thread(self.remove_file)
        return self

    def has_files(self) -> bool:
        return len(os.listdir(self.path)) > 0

    def copy(self, target: Path):
        if self.exists():
            if self.is_directory():
                self.copy_tree(target)
            else:
                try:
                    shutil.copy(self.path, target.path)
                except shutil.SameFileError:
                    pass
        else:
            raise FileNotFoundError(f"File not found: {self.path}")

    def copy_tree(self, target: Path):
        target.parent().generate_dirs()
        if self.exists():
            shutil.copytree(self.path, target.path, dirs_exist_ok=True)

    def read(self, create: bool = False) -> tbcml.Data:
        if self.exists():
            return tbcml.Data.from_file(self)
        elif create:
            self.write(tbcml.Data())
            return self.read()
        else:
            raise FileNotFoundError(f"File not found: {self.path}")

    def readable(self) -> bool:
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                f.read()
            except UnicodeDecodeError:
                return False
        return True

    def write(self, data: tbcml.Data):
        data.to_file(self)

    def get_files(self, regex: str | None = None) -> list[Path]:
        if self.exists():
            if regex is None:
                return [self.add(file) for file in os.listdir(self.path)]
            else:
                files: list[Path] = []
                for file in os.listdir(self.path):
                    if re.search(regex, file):
                        files.append(self.add(file))
                return files
        return []

    def get_files_recursive(self, regex: str | None = None) -> list[Path]:
        if not self.exists():
            return []
        if regex is None:
            files: list[Path] = []
            for root, _, files_str in os.walk(self.path):
                files.extend([self.add(root, file) for file in files_str])
            return files
        else:
            files: list[Path] = []
            for root, _, files_str in os.walk(self.path):
                for file_str in files_str:
                    file = self.add(root, file_str)
                    if re.search(regex, file.path):
                        files.append(self.add(root, file.path))
            return files

    def get_dirs_recursive(self) -> list[Path]:
        if not self.exists():
            return []
        dirs: list[Path] = []
        for root, dirnames, _ in os.walk(self.path):
            dirs.extend([self.add(root, dir) for dir in dirnames])
        return dirs

    def get_dirs(self) -> list[Path]:
        return [file for file in self.get_files() if file.is_directory()]

    def glob(self, pattern: str) -> list[Path]:
        return [Path(path) for path in glob.glob(self.add(pattern).path)]

    def recursive_glob(self, pattern: str) -> list[Path]:
        return [
            Path(path)
            for path in glob.glob(self.add("**", pattern).path, recursive=True)
        ]

    def is_directory(self) -> bool:
        return os.path.isdir(self.path)

    def change_name(self, name: str) -> Path:
        return self.parent().add(name)

    def rename(self, name: str, overwrite: bool = False):
        if not self.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        new_path = self.change_name(name)
        if new_path.path == self.path:
            return new_path
        if new_path.exists():
            if overwrite:
                new_path.remove()
            else:
                raise FileExistsError(f"File already exists: {new_path}")
        os.rename(self.path, new_path.path)
        return new_path

    def parent(self) -> Path:
        return Path(os.path.dirname(self.path))

    def change_extension(self, extension: str) -> Path:
        if extension.startswith("."):
            extension = extension[1:]
        return Path(self.path.rsplit(".", 1)[0] + "." + extension)

    def remove_extension(self) -> Path:
        return Path(self.path.rsplit(".", 1)[0])

    def get_extension(self) -> str:
        try:
            return self.path.rsplit(".", 1)[1]
        except IndexError:
            return ""

    def get_file_name(self) -> str:
        return os.path.basename(self.path)

    def get_file_name_path(self) -> Path:
        return Path(self.get_file_name())

    def get_file_name_without_extension(self) -> str:
        return self.get_file_name().rsplit(".", 1)[0]

    def get_file_size(self) -> int:
        return os.path.getsize(self.path)

    def get_absolute_path(self) -> Path:
        return Path(os.path.abspath(self.path))

    def remove_prefix(self, prefix: str) -> Path:
        return Path(self.path.removeprefix(prefix))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.path == other
        if not isinstance(other, Path):
            return False
        return self.path == other.path

    def __hash__(self) -> int:
        return hash(self.path)


PathStr = Path | str
"""Type alias for a tbcml.Path or a str."""
