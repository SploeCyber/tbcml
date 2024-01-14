import enum
import os
from typing import Any, Optional
from tbcml import core


class BCUFileGroup:
    def __init__(self, bcu_files: list["BCUFile"]) -> None:
        """
        Initialize a BCUFileGroup object.

        Args:
            bcu_files (list[BCUFile]): The list of BCU files.
        """
        self.bcu_files = bcu_files

    def get_file_by_name(self, name: str) -> Optional["BCUFile"]:
        """
        Get a BCU file by name.

        Args:
            name (str): The name of the file.

        Returns:
            Optional[BCUFile]: The BCU file.
        """
        for bcu_file in self.bcu_files:
            if bcu_file.name == name:
                return bcu_file
        return None

    def get_files_by_prefix(self, prefix: str) -> list["BCUFile"]:
        """
        Get a list of BCU files by prefix.

        Args:
            prefix (str): The prefix of the file.

        Returns:
            list[BCUFile]: The list of BCU files.
        """
        files: list[BCUFile] = []
        for bcu_file in self.bcu_files:
            if bcu_file.name.startswith(prefix):
                files.append(bcu_file)
        return files


class BCUForm:
    def __init__(
        self,
        form_data: dict[str, Any],
        anims: "BCUFileGroup",
        cat_id: int,
        form: "core.CatFormType",
    ):
        self.form_data = form_data
        self.cat_id = cat_id
        self.form = form
        self.id = self.form_data["anim"]["id"]
        self.name = self.form_data["names"]["dat"][0]["val"]
        self.description = self.form_data["description"]["dat"][0]["val"].split("<br>")
        self.anims = anims
        anim = self.load_anim()
        if anim is None:
            return None
        self.anim = anim

        upgrade_icon = self.load_display_icon()
        if upgrade_icon is None:
            return None
        self.upgrade_icon = upgrade_icon

        deploy_icon = self.load_deploy_icon()
        if deploy_icon is None:
            return None
        self.deploy_icon = deploy_icon

    def get_cat_id_form(self) -> Optional[tuple[int, "core.CatFormType"]]:
        img_name = self.anim.texture.metadata.img_name.get()
        cat_id = int(img_name[:3])
        form_str = img_name[4:5]
        try:
            form_type = core.CatFormType(form_str)
        except ValueError:
            return None
        return cat_id, form_type

    def get_mamodel_name(self) -> str:
        return f"{self.get_cat_id_str()}_{self.form.value}.mamodel"

    def get_imgcut_name(self) -> str:
        return f"{self.get_cat_id_str()}_{self.form.value}.imgcut"

    def get_sprite_name(self) -> str:
        return f"{self.get_cat_id_str()}_{self.form.value}.png"

    def get_maanim_names(self) -> list[str]:
        maanims = self.anims.get_files_by_prefix("maanim")
        maanim_names: list[str] = []
        for maanim in maanims:
            maanim_id = core.AnimType.from_bcu_str(maanim.name)
            if maanim_id is None:
                continue
            index_str = core.PaddedInt(maanim_id.value, 2).to_str()
            maanim_names.append(
                f"{self.get_cat_id_str()}_{self.form.value}{index_str}.maanim"
            )
        return maanim_names

    def get_maanim_data(self) -> list["core.Data"]:
        maanims = self.anims.get_files_by_prefix("maanim")
        maanim_data: list["core.Data"] = []
        for maanim in maanims:
            maanim_id = core.AnimType.from_bcu_str(maanim.name)
            if maanim_id is None:
                continue
            maanim_data.append(maanim.data)
        return maanim_data

    def load_anim(self) -> Optional["core.Model"]:
        sprite = self.anims.get_file_by_name("sprite.png")
        imgcut = self.anims.get_file_by_name("imgcut.txt")
        mamodel = self.anims.get_file_by_name("mamodel.txt")
        if sprite is None or imgcut is None or mamodel is None:
            return None
        model = core.Model().read_data(
            self.get_sprite_name(),
            sprite.data,
            self.get_imgcut_name(),
            imgcut.data,
            self.get_maanim_names(),
            self.get_maanim_data(),
            self.get_mamodel_name(),
            mamodel.data,
        )
        return model

    def load_display_icon(self) -> Optional["core.BCImage"]:
        display_file = self.anims.get_file_by_name("icon_display.png")
        if display_file is None:
            return None

        return core.BCImage.from_data(display_file.data)

    def load_deploy_icon(self) -> Optional["core.BCImage"]:
        deploy_file = self.anims.get_file_by_name("icon_deploy.png")
        if deploy_file is None:
            return None

        return core.BCImage.from_data(deploy_file.data)

    def get_cat_id_str(self):
        return core.PaddedInt(self.cat_id, 3).to_str()

    def to_cat_form(self, cat_id: int, form: "core.CatFormType") -> "core.CatForm":
        self.cat_id = cat_id
        self.form = form
        self.anim.mamodel.dup_ints()
        frm = core.CatForm(self.form)
        frm.stats = self.to_stats()
        frm.name.set(self.name)
        frm.description.set(self.description)
        frm.anim = self.anim
        frm.upgrade_icon = self.upgrade_icon
        frm.deploy_icon = self.deploy_icon
        frm.set_cat_id(self.cat_id)
        frm.set_form(self.form)
        frm.format_bcu_deploy_icon()
        frm.format_bcu_upgrade_icon()
        return frm

    def to_stats(self) -> "core.FormStats":
        stats = core.FormStats()
        base_stats = self.form_data["du"]
        traits = base_stats["traits"]
        procs = base_stats["rep"]["proc"]
        traits = sorted(traits, key=lambda x: x["id"])
        stats.hp.set(base_stats["hp"])
        stats.kbs.set(base_stats["hb"])
        stats.speed.set(base_stats["speed"])
        stats.attack_1_damage.set(base_stats["atks"]["pool"][0]["atk"])
        stats.attack_interval.set(base_stats["tba"] // 2)
        stats.attack_range.set(base_stats["range"])
        stats.cost.set(base_stats["price"])
        stats.recharge_time.set(base_stats["resp"] // 2)
        stats.collision_width.set(base_stats["width"])
        stats.target_red.set(self.get_trait_by_id(traits, 0))
        stats.area_attack.set(base_stats["atks"]["pool"][0]["range"])
        stats.min_z_layer.set(base_stats["front"])
        stats.max_z_layer.set(base_stats["back"])
        stats.target_floating.set(self.get_trait_by_id(traits, 1))
        stats.target_black.set(self.get_trait_by_id(traits, 2))
        stats.target_metal.set(self.get_trait_by_id(traits, 3))
        stats.target_traitless.set(self.get_trait_by_id(traits, 9))
        stats.target_angel.set(self.get_trait_by_id(traits, 4))
        stats.target_alien.set(self.get_trait_by_id(traits, 5))
        stats.target_zombie.set(self.get_trait_by_id(traits, 6))
        stats.strong.set(self.check_ability(base_stats["abi"], 0))
        stats.knockback_prob.set(self.get_proc_prob(procs, "KB"))
        stats.freeze_prob.set(self.get_proc_prob(procs, "STOP"))
        stats.freeze_duration.set(self.get_proc_time(procs, "STOP"))
        stats.slow_prob.set(self.get_proc_prob(procs, "SLOW"))
        stats.slow_duration.set(self.get_proc_time(procs, "SLOW"))
        stats.resistant.set(self.check_ability(base_stats["abi"], 1))
        stats.insane_damage.set(self.check_ability(base_stats["abi"], 2))
        stats.crit_prob.set(self.get_proc_prob(procs, "CRIT"))
        stats.attacks_only.set(self.check_ability(base_stats["abi"], 3))
        stats.extra_money.set(bool(self.get_proc_mult(procs, "BOUNTY") // 100))
        stats.base_destroyer.set(bool(self.get_proc_mult(procs, "ATKBASE") // 300))
        stats.wave_level.set(
            max(
                self.get_proc_level(procs, "WAVE"),
                self.get_proc_level(procs, "MINIWAVE"),
            )
        )
        stats.weaken_prob.set(self.get_proc_prob(procs, "WEAK"))
        stats.weaken_duration.set(self.get_proc_time(procs, "WEAK"))
        stats.strengthen_hp_start_percentage.set(self.get_proc_health(procs, "STRONG"))
        stats.strengthen_hp_boost_percentage.set(self.get_proc_mult(procs, "STRONG"))
        stats.lethal_strike_prob.set(self.get_proc_prob(procs, "LETHAL"))
        stats.is_metal.set(self.check_ability(base_stats["abi"], 4))
        stats.attack_1_ld_start.set(base_stats["atks"]["pool"][0]["ld0"])
        stats.attack_1_ld_range.set(
            base_stats["atks"]["pool"][0]["ld1"] - stats.attack_1_ld_start.get()
        )
        stats.wave_immunity.set(bool(self.get_proc_mult(procs, "IMUWAVE")))
        stats.wave_blocker.set(self.check_ability(base_stats["abi"], 5))
        stats.knockback_immunity.set(bool(self.get_proc_mult(procs, "IMUKB")))
        stats.freeze_immunity.set(bool(self.get_proc_mult(procs, "IMUSTOP")))
        stats.slow_immunity.set(bool(self.get_proc_mult(procs, "IMUSLOW")))
        stats.weaken_immunity.set(bool(self.get_proc_mult(procs, "IMUWEAK")))
        stats.zombie_killer.set(self.check_ability(base_stats["abi"], 9))
        stats.witch_killer.set(self.check_ability(base_stats["abi"], 10))
        stats.target_witch.set(self.check_ability(base_stats["abi"], 10))
        stats.attacks_before_set_attack_state.set(base_stats["loop"])
        stats.attack_state.set((2 if self.check_ability(base_stats["abi"], 11) else 0))
        stats.attack_2_damage.set(self.get_attack(base_stats["atks"]["pool"], 1, "atk"))
        stats.attack_2_damage.set(self.get_attack(base_stats["atks"]["pool"], 2, "atk"))
        stats.attack_1_foreswing.set(
            self.get_attack(base_stats["atks"]["pool"], 0, "pre")
        )
        stats.attack_2_foreswing.set(
            self.get_attack(base_stats["atks"]["pool"], 1, "pre")
        )
        stats.attack_2_foreswing.set(
            self.get_attack(base_stats["atks"]["pool"], 2, "pre")
        )
        stats.attack_2_use_ability.set(True)
        stats.attack_2_use_ability.set(True)
        stats.soul_model_anim_id.set(base_stats["death"]["id"])
        stats.barrier_break_prob.set(self.get_proc_prob(procs, "BREAK"))
        stats.warp_prob.set(self.get_proc_prob(procs, "WARP"))
        stats.warp_duration.set(self.get_proc_time(procs, "WARP"))
        stats.warp_min_range.set(self.get_proc_value(procs, "WARP", "dis") * 4)
        stats.warp_max_range.set(self.get_proc_value(procs, "WARP", "dis") * 4)
        stats.warp_blocker.set(bool(self.get_proc_mult(procs, "IMUWARP")))
        stats.target_eva.set(self.check_ability(base_stats["abi"], 13))
        stats.eva_killer.set(self.check_ability(base_stats["abi"], 13))
        stats.target_relic.set(self.get_trait_by_id(traits, 8))
        stats.curse_immunity.set(bool(self.get_proc_mult(procs, "IMUCURSE")))
        stats.insanely_tough.set(self.check_ability(base_stats["abi"], 15))
        stats.insane_damage.set(self.check_ability(base_stats["abi"], 16))
        stats.savage_blow_prob.set(self.get_proc_prob(procs, "SATK"))
        stats.savage_blow_damage_addition.set(self.get_proc_mult(procs, "SATK"))
        stats.dodge_prob.set(self.get_proc_prob(procs, "IMUATK"))
        stats.dodge_duration.set(self.get_proc_time(procs, "IMUATK"))
        stats.surge_prob.set(self.get_proc_prob(procs, "VOLC"))
        stats.surge_start.set(int(self.get_proc_value(procs, "VOLC", "dis_0")) * 4)
        stats.surge_range.set(
            (int(self.get_proc_value(procs, "VOLC", "dis_1")) * 4)
            - stats.surge_start.get()
        )
        stats.surge_level.set(self.get_proc_value(procs, "VOLC", "time") // 20)
        stats.toxic_immunity.set(bool(self.get_proc_mult(procs, "IMUPOIATK")))
        stats.surge_immunity.set(bool(self.get_proc_mult(procs, "IMUVOLC")))
        stats.curse_prob.set(self.get_proc_prob(procs, "CURSE"))
        stats.curse_duration.set(self.get_proc_time(procs, "CURSE"))
        stats.wave_is_mini.set(self.get_proc_prob(procs, "MINIWAVE") != 0)
        stats.shield_pierce_prob.set(self.get_proc_prob(procs, "SHIELDBREAK"))
        stats.target_aku.set(self.get_trait_by_id(traits, 7))
        stats.collossus_slayer.set(self.check_ability(base_stats["abi"], 17))
        stats.soul_strike.set(self.check_ability(base_stats["abi"], 18))
        stats.attack_2_ld_flag.set(
            self.get_attack(base_stats["atks"]["pool"], 1, "ld") != 0
        )
        stats.attack_2_ld_start.set(
            self.get_attack(base_stats["atks"]["pool"], 1, "ld0")
        )
        stats.attack_2_ld_range.set(
            (
                self.get_attack(base_stats["atks"]["pool"], 1, "ld1")
                - stats.attack_2_ld_start.get()
            )
        )
        stats.attack_2_ld_flag.set(
            self.get_attack(base_stats["atks"]["pool"], 2, "ld") != 0
        )
        stats.attack_2_ld_start.set(
            self.get_attack(base_stats["atks"]["pool"], 2, "ld0")
        )
        stats.attack_2_ld_range.set(
            (
                self.get_attack(base_stats["atks"]["pool"], 2, "ld1")
                - stats.attack_2_ld_start.get()
            )
        )
        stats.behemoth_slayer.set(self.get_proc_prob(procs, "BSTHUNT") != 0)
        stats.behemoth_dodge_prob.set(self.get_proc_prob(procs, "BSTHUNT"))
        stats.behemoth_dodge_duration.set(self.get_proc_time(procs, "BSTHUNT"))
        stats.attack_1_use_ability.set(True)
        stats.counter_surge.set(self.check_ability(base_stats["abi"], 19))

        return stats

    @staticmethod
    def get_trait_by_id(traits: list[dict[str, Any]], id: int) -> bool:
        for trait in traits:
            if trait["id"] == id:
                return True
        return False

    @staticmethod
    def check_ability(abi: int, id: int) -> bool:
        has_ability = abi & (1 << id) != 0
        return has_ability

    @staticmethod
    def get_proc_value(procs: dict[str, dict[str, int]], proc_name: str, key: str):
        if proc_name in procs:
            return int(procs[proc_name][key])
        return 0

    @staticmethod
    def get_proc_prob(procs: dict[str, dict[str, int]], proc_name: str):
        return BCUForm.get_proc_value(procs, proc_name, "prob")

    @staticmethod
    def get_proc_time(procs: dict[str, dict[str, int]], proc_name: str):
        return BCUForm.get_proc_value(procs, proc_name, "time")

    @staticmethod
    def get_proc_level(procs: dict[str, dict[str, int]], proc_name: str):
        return BCUForm.get_proc_value(procs, proc_name, "lv")

    @staticmethod
    def get_proc_health(procs: dict[str, dict[str, int]], proc_name: str):
        return BCUForm.get_proc_value(procs, proc_name, "health")

    @staticmethod
    def get_proc_mult(procs: dict[str, dict[str, int]], proc_name: str):
        return BCUForm.get_proc_value(procs, proc_name, "mult")

    @staticmethod
    def get_attack(attack_data: list[dict[str, Any]], attack_id: int, key: str):
        try:
            return attack_data[attack_id][key]
        except IndexError:
            return 0


class BCUCat:
    def __init__(
        self,
        unit_data: dict[str, Any],
        anims: list[list["BCUFile"]],
        cat_id: int,
    ):
        self.unit_data = unit_data
        forms = self.unit_data["val"]["forms"]
        self.local_id = self.unit_data["val"]["id"]["id"]
        self.rarity = self.unit_data["val"]["rarity"]
        self.max_base_level = self.unit_data["val"]["max"]
        self.max_plus_level = self.unit_data["val"]["maxp"]
        self.anims = anims
        self.forms: list[BCUForm] = []
        for i, (form_data, form_anims) in enumerate(zip(forms, anims)):
            self.forms.append(
                BCUForm(
                    form_data,
                    BCUFileGroup(form_anims),
                    cat_id,
                    core.CatFormType.from_index(i),
                )
            )

    def to_cat(
        self,
        cat_id: int,
    ) -> "core.Cat":
        forms: dict[core.CatFormType, core.CatForm] = {}
        for form in self.forms:
            forms[form.form] = form.to_cat_form(cat_id, form.form)

        unit_buy = core.UnitBuy()

        unit_buy.rarity.set(self.rarity)
        unit_buy.max_base_no_catseye.set(self.max_base_level)
        unit_buy.max_plus.set(self.max_plus_level)
        unit_buy.max_base_catseye.set(self.max_base_level)
        unit_buy.set_obtainable(True)

        nypb = core.NyankoPictureBook()
        nypb.is_displayed_in_cat_guide.set(True)

        unit = core.Cat(
            cat_id,
        )
        unit.forms = forms
        unit.unitbuy = unit_buy
        unit.set_cat_id(cat_id)
        return unit

    def get_cat_id(self) -> int:
        for form in self.forms:
            return form.cat_id
        return -1


class BCUEnemy:
    def __init__(
        self, enemy_data: dict[str, Any], anims: "BCUFileGroup", enemy_id: int
    ):
        self.enemy_data = enemy_data
        self.enemy_id = enemy_id
        self.anims = anims
        self.id = self.enemy_data["anim"]["id"]
        self.local_id = self.enemy_data["id"]["id"]
        self.name = self.enemy_data["names"]["dat"][0]["val"]
        self.descritpion = self.enemy_data["description"]["dat"][0]["val"].split("<br>")
        anim = self.load_anim()
        if anim is None:
            return None
        self.anim = anim

    def get_mamodel_name(self) -> str:
        return f"{self.get_enemy_id_str()}_e.mamodel"

    def get_imgcut_name(self) -> str:
        return f"{self.get_enemy_id_str()}_e.imgcut"

    def get_sprite_name(self) -> str:
        return f"{self.get_enemy_id_str()}_e.png"

    def get_maanim_names(self) -> list[str]:
        maanims = self.anims.get_files_by_prefix("maanim")
        maanim_names: list[str] = []
        for maanim in maanims:
            maanim_id = core.AnimType.from_bcu_str(maanim.name)
            if maanim_id is None:
                continue
            index_str = core.PaddedInt(maanim_id.value, 2).to_str()
            maanim_names.append(f"{self.get_enemy_id_str()}_e{index_str}.maanim")
        return maanim_names

    def get_maanim_data(self) -> list["core.Data"]:
        maanims = self.anims.get_files_by_prefix("maanim")
        maanim_data: list["core.Data"] = []
        for maanim in maanims:
            maanim_id = core.AnimType.from_bcu_str(maanim.name)
            if maanim_id is None:
                continue
            maanim_data.append(maanim.data)
        return maanim_data

    def load_anim(self) -> Optional["core.Model"]:
        sprite = self.anims.get_file_by_name("sprite.png")
        imgcut = self.anims.get_file_by_name("imgcut.txt")
        mamodel = self.anims.get_file_by_name("mamodel.txt")
        if sprite is None or imgcut is None or mamodel is None:
            return None
        model = core.Model().read_data(
            self.get_sprite_name(),
            sprite.data,
            self.get_imgcut_name(),
            imgcut.data,
            self.get_maanim_names(),
            self.get_maanim_data(),
            self.get_mamodel_name(),
            mamodel.data,
        )
        return model

    def get_enemy_id(self) -> Optional[int]:
        img_name = self.anim.texture.metadata.img_name.get()
        try:
            enemy_id = int(img_name[:3])
        except ValueError:
            return None
        return enemy_id

    def get_enemy_id_str(self):
        return core.PaddedInt(self.enemy_id, 3).to_str()

    def to_enemy(self, enemy_id: int) -> "core.Enemy":
        for maanim in self.anim.anims:
            index = core.AnimType.from_bcu_str(maanim.name)
            if index is None:
                continue
            index_str = core.PaddedInt(index.value, 2).to_str()
            maanim.name = f"{self.get_enemy_id_str()}_e{index_str}.maanim"
        enemy = core.Enemy(
            enemy_id,
        )
        enemy.stats = self.to_stats()
        enemy.name.set(self.name)
        enemy.description.set(self.descritpion)
        enemy.anim = self.anim
        enemy.set_enemy_id(enemy_id)
        return enemy

    def to_stats(self) -> "core.EnemyStats":
        stats = core.EnemyStats()
        base_stats = self.enemy_data["de"]
        traits = base_stats["traits"]
        procs = base_stats["rep"]["proc"]
        traits = sorted(traits, key=lambda x: x["id"])

        stats.hp.set(base_stats["hp"])
        stats.kbs.set(base_stats["hb"])
        stats.speed.set(base_stats["speed"])
        stats.attack_1_damage.set(base_stats["atks"]["pool"][0]["atk"])
        stats.attack_interval.set(base_stats["tba"])
        stats.attack_range.set(base_stats["range"])
        stats.money_drop.set(base_stats["drop"])
        stats.collision_width.set(base_stats["width"])
        stats.red.set(BCUForm.get_trait_by_id(traits, 0))
        stats.area_attack.set(base_stats["atks"]["pool"][0]["range"])
        stats.floating.set(BCUForm.get_trait_by_id(traits, 1))
        stats.black.set(BCUForm.get_trait_by_id(traits, 2))
        stats.metal.set(BCUForm.get_trait_by_id(traits, 3))
        stats.traitless.set(BCUForm.get_trait_by_id(traits, 9))
        stats.angel.set(BCUForm.get_trait_by_id(traits, 4))
        stats.alien.set(BCUForm.get_trait_by_id(traits, 5))
        stats.zombie.set(BCUForm.get_trait_by_id(traits, 6))
        stats.knockback_prob.set(BCUForm.get_proc_prob(procs, "KB"))
        stats.freeze_prob.set(BCUForm.get_proc_prob(procs, "STOP"))
        stats.freeze_duration.set(BCUForm.get_proc_time(procs, "STOP"))
        stats.slow_prob.set(BCUForm.get_proc_prob(procs, "SLOW"))
        stats.slow_duration.set(BCUForm.get_proc_time(procs, "SLOW"))
        stats.crit_prob.set(BCUForm.get_proc_prob(procs, "CRIT"))
        stats.base_destroyer.set(bool(BCUForm.get_proc_mult(procs, "ATKBASE") // 300))
        stats.wave_is_mini.set(
            bool(
                max(
                    BCUForm.get_proc_prob(procs, "WAVE"),
                    BCUForm.get_proc_prob(procs, "MINIWAVE"),
                )
            )
        )
        stats.wave_level.set(
            max(
                BCUForm.get_proc_level(procs, "WAVE"),
                BCUForm.get_proc_level(procs, "MINIWAVE"),
            )
        )
        stats.weaken_prob.set(BCUForm.get_proc_prob(procs, "WEAK"))
        stats.weaken_duration.set(BCUForm.get_proc_time(procs, "WEAK"))
        stats.strengthen_hp_start_percentage.set(
            BCUForm.get_proc_health(procs, "STRONG")
        )
        stats.strengthen_hp_boost_percentage.set(BCUForm.get_proc_mult(procs, "STRONG"))
        stats.survive_lethal_strike_prob.set(BCUForm.get_proc_prob(procs, "LETHAL"))
        stats.attack_1_ld_start.set(base_stats["atks"]["pool"][0]["ld0"])
        stats.attack_1_ld_range.set(
            (base_stats["atks"]["pool"][0]["ld1"] - stats.attack_1_ld_start)
        )
        stats.wave_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUWAVE")))
        stats.wave_blocker.set(BCUForm.check_ability(base_stats["abi"], 5))
        stats.knockback_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUKB")))
        stats.freeze_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUSTOP")))
        stats.slow_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUSLOW")))
        stats.weaken_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUWEAK")))
        stats.burrow_count.set(BCUForm.get_proc_value(procs, "BURROW", "count"))
        stats.burrow_distance.set(BCUForm.get_proc_value(procs, "BURROW", "dis") * 4)
        stats.revive_count.set(BCUForm.get_proc_value(procs, "REVIVE", "count"))
        stats.revive_time.set(BCUForm.get_proc_time(procs, "REVIVE"))
        stats.revive_hp_percentage.set(BCUForm.get_proc_health(procs, "REVIVE"))
        stats.witch.set(BCUForm.get_trait_by_id(traits, 10))
        stats.base.set(BCUForm.get_trait_by_id(traits, 14))
        stats.attacks_before_set_attack_state.set(base_stats["loop"])
        stats.attack_state.set(
            (2 if BCUForm.check_ability(base_stats["abi"], 11) else 0)
        )
        stats.attack_2_damage.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 1, "atk")
        )
        stats.attack_2_damage.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 2, "atk")
        )
        stats.attack_1_foreswing.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 0, "pre")
        )
        stats.attack_2_foreswing.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 1, "pre")
        )
        stats.attack_2_foreswing.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 2, "pre")
        )
        stats.attack_2_use_ability.set(True)
        stats.attack_2_use_ability.set(True)
        stats.soul_model_anim_id.set(base_stats["death"]["id"])
        stats.barrier_hp.set(BCUForm.get_proc_health(procs, "BARRIER"))
        stats.warp_prob.set(BCUForm.get_proc_prob(procs, "WARP"))
        stats.warp_duration.set(BCUForm.get_proc_time(procs, "WARP"))
        stats.warp_min_range.set(BCUForm.get_proc_value(procs, "WARP", "dis") * 4)
        stats.warp_max_range.set(BCUForm.get_proc_value(procs, "WARP", "dis") * 4)
        stats.starred_alien.set(base_stats["star"])
        stats.warp_blocker.set(bool(BCUForm.get_proc_mult(procs, "IMUWARP")))
        stats.eva_angel.set(BCUForm.get_trait_by_id(traits, 10))
        stats.relic.set(BCUForm.get_trait_by_id(traits, 8))
        stats.curse_prob.set(BCUForm.get_proc_prob(procs, "CURSE"))
        stats.curse_duration.set(BCUForm.get_proc_time(procs, "CURSE"))
        stats.surge_prob.set(BCUForm.get_proc_prob(procs, "VOLC"))
        stats.savage_blow_prob.set(BCUForm.get_proc_prob(procs, "SATK"))
        stats.savage_blow_damage_addition.set(BCUForm.get_proc_mult(procs, "SATK"))
        stats.dodge_prob.set(BCUForm.get_proc_prob(procs, "IMUATK"))
        stats.dodge_duration.set(BCUForm.get_proc_time(procs, "IMUATK"))
        stats.toxic_prob.set(BCUForm.get_proc_prob(procs, "POIATK"))
        stats.toxic_hp_percentage.set(BCUForm.get_proc_mult(procs, "POIATK"))
        stats.surge_start.set(int(BCUForm.get_proc_value(procs, "VOLC", "dis_0")) * 4)
        stats.surge_range.set(
            (int(BCUForm.get_proc_value(procs, "VOLC", "dis_1")) * 4)
            - stats.surge_start.get()
        )
        stats.surge_level.set(BCUForm.get_proc_value(procs, "VOLC", "time") // 20)
        stats.surge_immunity.set(bool(BCUForm.get_proc_mult(procs, "IMUVOLC")))
        stats.wave_is_mini.set(BCUForm.get_proc_prob(procs, "MINIWAVE") != 0)
        stats.shield_hp.set(BCUForm.get_proc_health(procs, "SHIELD"))
        stats.sheild_kb_heal_percentage.set(
            BCUForm.get_proc_value(procs, "SHIELD", "regen")
        )
        stats.death_surge_prob.set(BCUForm.get_proc_prob(procs, "DEATHSURGE"))
        stats.death_surge_start.set(
            (int(BCUForm.get_proc_value(procs, "DEATHSURGE", "dis_0")) * 4)
        )
        stats.death_surge_range.set(
            (int(BCUForm.get_proc_value(procs, "DEATHSURGE", "dis_1")) * 4)
            - stats.death_surge_start.get()
        )
        stats.death_surge_level.set(
            (BCUForm.get_proc_value(procs, "DEATHSURGE", "time") // 20)
        )
        stats.aku.set(BCUForm.get_trait_by_id(traits, 7))
        stats.baron.set(BCUForm.get_trait_by_id(traits, 12))
        stats.attack_2_ld_flag.set(
            (
                BCUForm.get_attack(base_stats["atks"]["pool"], 1, "ld0") != 0
                or BCUForm.get_attack(base_stats["atks"]["pool"], 1, "ld1") != 0
            )
        )
        stats.attack_2_ld_start.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 1, "ld0")
        )
        stats.attack_2_ld_range.set(
            (
                BCUForm.get_attack(base_stats["atks"]["pool"], 1, "ld1")
                - stats.attack_2_ld_start.get()
            )
        )
        stats.attack_2_ld_flag.set(
            (
                BCUForm.get_attack(base_stats["atks"]["pool"], 2, "ld0") != 0
                or BCUForm.get_attack(base_stats["atks"]["pool"], 2, "ld1") != 0
            )
        )
        stats.attack_2_ld_start.set(
            BCUForm.get_attack(base_stats["atks"]["pool"], 2, "ld0")
        )
        stats.attack_2_ld_range.set(
            (
                BCUForm.get_attack(base_stats["atks"]["pool"], 2, "ld1")
                - stats.attack_2_ld_start.get()
            )
        )
        stats.behemoth.set(BCUForm.get_trait_by_id(traits, 13))
        stats.counter_surge.set(BCUForm.check_ability(base_stats["abi"], 19))

        return stats


class BCUFileTypes(enum.Enum):
    ANIMS = "animations"
    MUSIC = "musics"
    PACK = "pack.json"


class BCUFile:
    def __init__(
        self,
        file_info: dict[str, Any],
        enc_data: "core.Data",
        key: "core.Data",
        iv: "core.Data",
    ):
        self.path: str = file_info["path"]
        self.size = file_info["size"]
        self.offset = file_info["offset"]
        self.name = os.path.basename(self.path)
        self.type_str = self.path.split("/")[1]
        self.key = key
        self.iv = iv
        self.padded_size = self.size + (16 - self.size % 16)
        self.enc_data = enc_data[self.offset : self.offset + self.padded_size]
        self.data = self.decrypt()

    def get_type(self) -> Optional[BCUFileTypes]:
        try:
            return BCUFileTypes(self.type_str)
        except ValueError:
            return None

    def decrypt(self) -> "core.Data":
        aes = core.AesCipher(self.key.to_bytes(), self.iv.to_bytes())
        data = aes.decrypt(self.enc_data)
        return data[: self.size]


class BCUZip:
    def __init__(
        self,
        enc_data: "core.Data",
    ):
        self.enc_data = enc_data
        self.iv, self.key = self.get_iv_key()
        self.json, self.enc_file_data = self.decrypt()
        self.read_json_info()
        self.files = self.load_files()
        pack_json = self.load_pack_json()
        if pack_json is None:
            raise ValueError("Pack json not found")
        self.pack_json = pack_json
        self.cats = self.load_units()
        self.enemies = self.load_enemies()

    @staticmethod
    def from_path(path: "core.Path") -> "BCUZip":
        return BCUZip(core.Data.from_file(path))

    def get_iv_key(self) -> tuple["core.Data", "core.Data"]:
        iv_str = "battlecatsultimate"
        iv = core.Hash(core.HashAlgorithm.MD5).get_hash(core.Data(iv_str))
        key = self.enc_data[0x10:0x20]
        return iv, key

    def decrypt(self) -> tuple["core.JsonFile", "core.Data"]:
        json_length = self.enc_data[0x20:0x24].to_int_little()
        json_length_pad = 16 * (json_length // 16 + 1)
        json_data = self.enc_data[0x24 : 0x24 + json_length_pad]
        aes = core.AesCipher(self.key.to_bytes(), self.iv.to_bytes())
        json_data = aes.decrypt(json_data)
        json_data = json_data[0:json_length]

        enc_file_data = self.enc_data[0x24 + json_length_pad :]

        json = core.JsonFile.from_data(json_data)

        return json, enc_file_data

    def read_json_info(self):
        self.desc = self.json["desc"]
        self.files_data = self.json["files"]

        self.bcu_version = self.desc["BCU_VERSION"]
        self.id = self.desc["id"]
        self.author = self.desc["author"]
        self.names = self.desc["names"]
        self.allow_anim = self.desc["allowAnim"]
        self.dependency = self.desc["dependency"]

    def load_files(self) -> list[BCUFile]:
        files: list[BCUFile] = []
        for file_info in self.files_data:
            files.append(BCUFile(file_info, self.enc_file_data, self.key, self.iv))
        return files

    def get_file(self, path: str) -> Optional[BCUFile]:
        for file in self.files:
            if file.path == path:
                return file
        return None

    def get_file_by_name(self, name: str) -> Optional[BCUFile]:
        for file in self.files:
            if file.name == name:
                return file
        return None

    def get_files_by_type(self, type: BCUFileTypes) -> list[BCUFile]:
        files: list[BCUFile] = []
        for file in self.files:
            if file.get_type() == type:
                files.append(file)
        return files

    def get_files_by_dir(self, dir: str) -> list[BCUFile]:
        files: list[BCUFile] = []
        for file in self.files:
            if os.path.basename(os.path.dirname(file.path)) == dir:
                files.append(file)
        return files

    def extract(self, output_dir: "core.Path"):
        output_dir = output_dir.add(self.get_name())
        for file in self.files:
            file_path = output_dir.add(file.path)
            file_dir = file_path.parent()
            file_dir.generate_dirs()
            file.data.to_file(file_path)

        json_path = output_dir.add("info.json")
        self.json.to_data().to_file(json_path)

    def get_name(self) -> str:
        return self.names["dat"][0]["val"]

    def load_pack_json(self) -> Optional["core.JsonFile"]:
        pack_file = self.get_file_by_name("pack.json")
        if pack_file is None:
            return None
        return core.JsonFile.from_data(pack_file.data)

    def load_units(self):
        units_data: list[Any] = self.pack_json["units"]["data"]
        units: list[BCUCat] = []
        for i, unit_data in enumerate(units_data):
            forms = unit_data["val"]["forms"]
            anims: list[list[BCUFile]] = []
            for form in forms:
                unit_id = form["anim"]["id"]
                anims.append(self.get_files_by_dir(unit_id))
            unit = BCUCat(
                unit_data,
                anims,
                i,
            )
            units.append(unit)
        return units

    def load_enemies(self):
        enemies_data: list[Any] = self.pack_json["enemies"]["data"]
        enemies: list[BCUEnemy] = []
        for i, enemy_data in enumerate(enemies_data):
            enemy_id = enemy_data["val"]["anim"]["id"]
            anims = self.get_files_by_dir(enemy_id)
            enemy = BCUEnemy(
                enemy_data["val"],
                BCUFileGroup(anims),
                i,
            )
            enemies.append(enemy)
        return enemies
