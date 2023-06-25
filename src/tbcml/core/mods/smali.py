"""A module for injecting smali code into the APK."""
from typing import Optional

from androguard.core.bytecodes.apk import APK  # type: ignore

from tbcml import core


class Smali:
    """A class to represent a smali file."""

    def __init__(self, class_code: str, class_name: str, function_sig_to_call: str):
        """Initializes the Smali

        Args:
            class_code (str): The actual smali code
            class_name (str): The name of the class
            function_sig_to_call (str): The signature of the function to call in onCreate
        """
        self.class_code = class_code
        self.class_name = class_name
        self.function_sig_to_call = function_sig_to_call

    @staticmethod
    def from_file(
        path: "core.Path", class_name: str, function_sig_to_call: str
    ) -> "Smali":
        """Creates a Smali from a smali file.

        Args:
            path (core.Path): Path to the smali file
            class_name (str): Class name to use
            function_sig_to_call (str): The signature of the function to call to run the class code

        Returns:
            Smali: The created Smali
        """
        data = path.read().to_str()
        return Smali(data, class_name, function_sig_to_call)


class SmaliSet:
    """A class to represent a set of smali files."""

    def __init__(self, smali_edits: dict[str, Smali]):
        """Initializes the SmaliSet

        Args:
            smali_edits (dict[str, Smali]): The smali edits
        """
        self.smali_edits = smali_edits

    def is_empty(self) -> bool:
        """Checks if the SmaliSet is empty.

        Returns:
            bool: Whether the SmaliSet is empty
        """
        return len(self.smali_edits) == 0

    @staticmethod
    def create_empty() -> "SmaliSet":
        """Creates an empty SmaliSet.

        Returns:
            SmaliSet: The created SmaliSet
        """
        return SmaliSet({})

    def add_to_zip(self, zip_file: "core.Zip"):
        """Adds the SmaliSet to a mod zip.

        Args:
            zip_file (core.Zip): The zip file to add the SmaliSet to
        """
        base_path = core.Path("smali")
        for smali in self.smali_edits.values():
            json_data = core.JsonFile.from_object(
                {"function_sig_to_call": smali.function_sig_to_call}
            )
            file_data = core.Data(smali.class_code)
            path = base_path.add(*smali.class_name.split(".")[:-1])
            path = path.add(smali.class_name.split(".")[-1] + ".smali")
            zip_file.add_file(path, file_data)
            zip_file.add_file(path.change_extension("json"), json_data.to_data())

    @staticmethod
    def from_zip(zip_file: "core.Zip") -> "SmaliSet":
        """Creates a SmaliSet from a mod zip.

        Args:
            zip_file (core.Zip): The zip file to create the SmaliSet from

        Returns:
            SmaliSet: The created SmaliSet
        """
        base_path = core.Path("smali")
        smali_edits = {}
        for file in zip_file.get_paths():
            if not file.path.startswith(base_path.to_str_forwards()):
                continue
            if not file.path.endswith(".smali"):
                continue

            path = core.Path(file.path)
            class_name = path.remove_extension().to_str_forwards()
            json_file = zip_file.get_file(path.change_extension("json"))
            if json_file is None:
                continue

            json_data = core.JsonFile.from_data(json_file)
            function_sig_to_call = json_data.get("function_sig_to_call")
            if function_sig_to_call is None:
                continue

            smali_edits[class_name] = Smali(
                file.to_str(), class_name, function_sig_to_call
            )
        return SmaliSet(smali_edits)

    def import_smali(self, other: "SmaliSet"):
        """Imports the smali from another SmaliSet.

        Args:
            other (SmaliSet): The SmaliSet to import from
        """
        self.smali_edits.update(other.smali_edits)

    def add(self, smali: Smali):
        """Adds a Smali to the SmaliSet.

        Args:
            smali (Smali): The Smali to add
        """
        self.smali_edits[smali.class_name] = smali

    def get_list(self) -> list[Smali]:
        """Gets the SmaliSet as a list.

        Returns:
            list[Smali]: The SmaliSet as a list
        """
        return list(self.smali_edits.values())


class SmaliHandler:
    """Injects smali into an apk.
    https://github.com/ksg97031/frida-gadget"""

    def __init__(self, apk: "core.Apk"):
        """Initializes the SmaliHandler

        Args:
            apk (core.Apk): The apk to inject into

        Raises:
            FileNotFoundError: If the main activity could not be found
        """
        self.apk = apk
        self.apk.extract_smali()
        self.andro_apk = APK(self.apk.apk_path.path)
        main_activity: str = self.andro_apk.get_main_activity()  # type: ignore
        if main_activity is None:  # type: ignore
            raise FileNotFoundError("Could not find main activity")
        main_activity_list = main_activity.split(".")
        main_activity_list[-1] += ".smali"
        self.main_activity = main_activity_list

    def find_main_activity_smali(self) -> Optional["core.Path"]:
        """Finds the main activity smali file

        Returns:
            Optional[core.Path]: The path to the main activity smali file
        """
        target_smali = None
        for smali_dir in self.apk.extracted_path.glob("smali*/"):
            target_smali = smali_dir.add(*self.main_activity)
            if target_smali.exists():
                break
        return target_smali

    def setup_injection(self) -> tuple[list[str], "core.Path"]:
        """Sets up the injection by finding the main activity smali file and reading it

        Raises:
            FileNotFoundError: If the main activity smali could not be found

        Returns:
            tuple[list[str], core.Path]: The main activity smali code and the path to the smali file
        """
        target_smali = self.find_main_activity_smali()
        if target_smali is None:
            raise FileNotFoundError(
                f"Could not find main activity smali: {self.main_activity}"
            )
        text = target_smali.read().to_str()
        text = text.split("\n")

        return text, target_smali

    def inject_into_on_create(self, smali_codes: list[Smali]):
        """Injects the smali code into the main activity's onCreate method

        Args:
            smali_codes (list[Smali]): The smali code to inject

        Raises:
            FileNotFoundError: If the main activity smali could not be found
        """
        text, target_smali = self.setup_injection()

        path = self.apk.extracted_path.add("smali").add("com").add("tbcml")
        path.generate_dirs()
        for smali_code in smali_codes:
            path = path.add(smali_code.class_name + ".smali")
            path.write(core.Data(smali_code.class_code))

        for i, line in enumerate(text):
            if line.startswith(".method") and "onCreate(" in line:
                for j, smali in enumerate(smali_codes):
                    text.insert(
                        i + 2 + j,
                        f"    invoke-static {{p0}}, Lcom/tbcml/{smali.class_name};->{smali.function_sig_to_call}",
                    )
                break

        text = "\n".join(text)
        target_smali.write(core.Data(text))

    def inject_load_library(self, library_name: str):
        """Injects the code to load a native library into the main activity's onCreate method

        Args:
            library_name (str): The name of the library to load
        """
        if library_name.startswith("lib"):
            library_name = library_name[3:]
        library_name = library_name.replace(".so", "")

        text, target_smali = self.setup_injection()

        inject_text = f"""
    const-string v0, "{library_name}"
    invoke-static {{v0}}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V

    const-string v0, "Loaded {library_name}"
    const-string v1, "TBCML"
    invoke-static {{v0, v1}}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I
        """

        for i, line in enumerate(text):
            if line.startswith(".method") and "onCreate(" in line:
                text.insert(i + 3, inject_text)
                break

        text = "\n".join(text)
        target_smali.write(core.Data(text))

    def get_data_load_smali(self) -> Smali:
        """Gets the smali code for the DataLoad class which is used to extract data.zip into the
        /data/data/jp.co.ponos.battlecats/files directory

        Returns:
            Smali: The smali code for the DataLoad class
        """
        path = core.AssetLoader.from_config().get_asset_file_path("DataLoad.smali")
        data = path.read().to_str()
        return Smali(data, "DataLoad", "Start(Landroid/content/Context;)V")

    @staticmethod
    def java_to_smali(
        java_code: str, class_name: str, func_sig: str, display_errors: bool = True
    ) -> Optional[Smali]:
        """Compiles java code into smali code

        Args:
            java_code (str): The java code to compile
            class_name (str): The name of the class
            func_sig (str): The function signature to call to start the class code
            display_errors (bool, optional): Whether to display errors if the compilation fails. Defaults to True.

        Returns:
            Optional[Smali]: The compiled smali code. None if the compilation failed
        """
        with core.TempFolder() as temp_folder:
            java_path = temp_folder.add("com").add("tbcml").add(f"{class_name}.java")
            java_path.parent().generate_dirs()
            java_path.write(core.Data(java_code))
            command = core.Command(
                f"javac --source 7 --target 7 '{java_path}' -d '{temp_folder}'"
            )
            result = command.run()
            if result.exit_code != 0:
                if display_errors:
                    print(result.result)
                return None

            dex_path = temp_folder.add("classes.dex")

            command = core.Command(
                f"dx --dex --output='{dex_path}' 'com/tbcml/{class_name}.class'",
                cwd=temp_folder,
            )
            result = command.run()
            if result.exit_code != 0:
                if display_errors:
                    print(result.result)
                return None

            smali_path = temp_folder.add("smali")

            baksmali_path = core.Path("lib", is_relative=True).add("baksmali.jar")
            command = core.Command(
                f"java -jar {baksmali_path} d '{dex_path}' -o '{smali_path}'"
            )
            result = command.run()
            if result.exit_code != 0:
                if display_errors:
                    print(result.result)
                return None

            smali_path = smali_path.add("com").add("tbcml").add(f"{class_name}.smali")
            smali_code = smali_path.read().to_str()
            return Smali(smali_code, class_name, func_sig)

    @staticmethod
    def java_to_smali_from_path(
        path: "core.Path",
        func_sig: str,
        display_errors: bool = True,
    ) -> Optional[Smali]:
        """Compiles java code into smali code

        Args:
            path (core.Path): The path to the java file
            func_sig (str): The function signature to call to start the class code
            display_errors (bool, optional): Whether to display errors if the compilation fails. Defaults to True.

        Returns:
            Optional[Smali]: The compiled smali code. None if the compilation failed
        """
        java_code = path.read().to_str()
        class_name = path.get_file_name_without_extension()
        return SmaliHandler.java_to_smali(
            java_code, class_name, func_sig, display_errors
        )
