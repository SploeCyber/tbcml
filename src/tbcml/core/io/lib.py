from tbcml import core
import lief  # type: ignore


class Lib:
    def __init__(self, architecture: str, path: "core.Path"):
        self.architecture = architecture
        self.path = path
        self.lib = self.parse()  # type: ignore
        self.data = path.read()

    def parse(self) -> lief.ELF.Binary:  # type: ignore
        return lief.parse(str(self.path))  # type: ignore

    def add_library(self, library_path: "core.Path"):
        self.lib.add_library(library_path.basename())  # type: ignore

    def write(self):
        self.lib.write(str(self.path))  # type: ignore

    def search(self, search: "core.Data", start: int = 0):
        return self.data.search(search, start)

    def read_int_list(self, start: int, length: int) -> list[int]:
        self.data.set_pos(start)
        return self.data.read_int_list(length)


class LibFiles:
    def __init__(self, apk: "core.Apk"):
        self.libs_folder = apk.extracted_path.add("lib")
        self.apk = apk
        self.so_files = self.get_so_files()
        self.modified_packs = self.get_modified_packs()
        self.modified_packs_hashes = self.get_all_pack_list_hashes()
        if self.apk.key is not None:
            self.change_key(self.apk.key)
        if self.apk.iv is not None:
            self.change_iv(self.apk.iv)

    def get_so_files(self):
        files: dict[str, "core.Data"] = {}
        for arc in self.libs_folder.get_dirs():
            arc_name = arc.basename()
            lib_path = self.apk.get_libnative_path(arc_name)
            files[arc_name] = lib_path.read()
        return files

    def get_modified_packs(self) -> list["core.Path"]:
        return self.apk.modified_packs_path.get_files()

    def get_all_pack_list_hashes(self):
        hashes: dict[str, core.Data] = {}
        for pack in self.modified_packs:
            hashes[pack.basename()] = core.Data(
                core.Hash(core.HashAlgorithm.MD5).get_hash(pack.read()).to_hex()
            )

        return hashes

    def replace_hashes_in_so(self):
        for arc, so in self.so_files.items():
            for pack_name, modified_hash in self.modified_packs_hashes.items():
                original_packs = self.get_original_packs_lists()
                original_Pack = None
                for pack in original_packs:
                    if pack.basename() == pack_name:
                        original_Pack = pack
                        break
                if original_Pack is None:
                    continue
                original_hash = core.Data(
                    core.Hash(core.HashAlgorithm.MD5)
                    .get_hash(original_Pack.read())
                    .to_hex()
                )
                so = so.replace(original_hash, modified_hash)
            self.so_files[arc] = so

    def replace_hashes_in_smali(self):
        smali_handler = self.apk.get_smali_handler()
        for pack_name, modified_hash in self.modified_packs_hashes.items():
            if pack_name.endswith("1.pack") and self.apk.is_java():
                pack_name = pack_name.replace("1.pack", "2.pack")
            original_packs = self.get_original_packs_lists()
            original_Pack = None
            for pack in original_packs:
                if pack.basename() == pack_name:
                    original_Pack = pack
                    break
            if original_Pack is None:
                continue
            original_hash = core.Data(
                core.Hash(core.HashAlgorithm.MD5)
                .get_hash(original_Pack.read())
                .to_hex()
            )
            smali_handler.replace_all_strings(
                original_hash.to_str(), modified_hash.to_str()
            )

    def get_duplicate_packs_lists(self) -> dict["core.Path", list["core.Path"]]:
        """
        Returns a dict where the keys are the modified packs and the values are the duplicate original packs

        Returns:
            dict[pathHandler.Path, list[pathHandler.Path]]: Duplicate packs
        """
        duplicates: dict[core.Path, list[core.Path]] = {}
        for pack in self.modified_packs:
            duplicates[pack] = []
            original_pack_path = self.get_pack_folder_original().add(pack.basename())
            if pack.basename().endswith("1.pack") and self.apk.is_java():
                original_pack_path = self.get_pack_folder_original().add(
                    pack.basename().replace("1.pack", "2.pack")
                )
            for original in self.get_pack_folder_original().get_files(
                regex=".*\\.pack|.*\\.list"
            ):
                if original.basename() == pack.basename():
                    continue
                if original_pack_path.read().to_bytes() == original.read().to_bytes():
                    duplicates[pack].append(original)

        return duplicates

    def get_original_packs_lists(self) -> list["core.Path"]:
        return self.get_pack_folder_original().get_files(regex=".*\\.pack|.*\\.list")

    def get_pack_folder_original(self):
        if self.apk.is_java():
            return self.apk.original_extracted_path.add("res").add("raw")
        else:
            return self.apk.original_extracted_path.add("assets")

    def write(self):
        for arc, so in self.so_files.items():
            lib_path = self.apk.get_libnative_path(arc)
            lib_path.write(so)

    def overwrite_duplicate_packs(self):
        duplicates = self.get_duplicate_packs_lists()
        for pack, originals in duplicates.items():
            for original in originals:
                original_path = self.apk.modified_packs_path.add(original.basename())
                original_path.write(pack.read())

    def patch(self):
        if self.apk.is_java():
            self.replace_hashes_in_smali()
        else:
            self.replace_hashes_in_so()
        self.overwrite_duplicate_packs()
        self.write()

    def change_key(self, key: str):
        orignal_key, _ = core.AesCipher.get_key_iv_from_cc(self.apk.country_code)
        key1 = core.Data(key[:16])
        key2 = core.Data(key[16:])

        orig_key1 = core.Data(orignal_key[:16])
        orig_key2 = core.Data(orignal_key[16:])

        for arc, so in self.so_files.items():
            so = so.replace(orig_key1, key1)
            so = so.replace(orig_key2, key2)
            self.so_files[arc] = so

    def change_iv(self, iv: str):
        _, original_iv = core.AesCipher.get_key_iv_from_cc(self.apk.country_code)
        iv1 = core.Data(iv[:16])
        iv2 = core.Data(iv[16:])

        orig_iv1 = core.Data(original_iv[:16])
        orig_iv2 = core.Data(original_iv[16:])

        for arc, so in self.so_files.items():
            so = so.replace(orig_iv1, iv1)
            so = so.replace(orig_iv2, iv2)
            self.so_files[arc] = so
