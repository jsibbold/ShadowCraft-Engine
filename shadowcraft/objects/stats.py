from shadowcraft.objects import procs
from shadowcraft.objects import proc_data
from shadowcraft.core import exceptions

class Stats(object):
    # For the moment, lets define this as raw stats from gear + race; AP is
    # only AP bonuses from gear and level.  Do not include multipliers like
    # Vitality and Sinister Calling; this is just raw stats.  See calcs page
    # rows 1-9 from my WotLK spreadsheets to see how these are typically
    # defined, though the numbers will need to updated for level 85.

    melee_hit_rating_conversion_values = {60:9.37931, 70:14.7905, 80:30.7548, 81:40.3836, 82:53.0304, 83:69.6653, 84:91.4738, 85:120.109001159667969}
    spell_hit_rating_conversion_values = {60:8, 70:12.6154, 80:26.232, 81:34.4448, 82:45.2318, 83:59.4204, 84:78.0218, 85:102.445999145507812}
    crit_rating_conversion_values = {60:14, 70:22.0769, 80:45.906, 81:60.2784, 82:79.1556, 83:103.986, 84:136.53799, 85:179.279998779296875}
    haste_rating_conversion_values = {60:10, 70:15.7692, 80:32.79, 81:43.056, 82:56.5397, 83:74.2755, 84:97.5272, 85:128.057006835937500}
    expertise_rating_conversion_values = {60:2.34483 * 4, 70:3.69761 * 4, 80:7.68869 * 4, 81:10.0959 * 4, 82:13.2576 * 4, 83:17.4163 * 4, 84:22.8685 * 4, 85:30.027200698852539 * 4}
    mastery_rating_conversion_values = {60:14, 70:22.0769, 80:45.906, 81:60.2784, 82:79.1556, 83:103.986, 84:136.53799, 85:179.279998779296875}

    def __init__(self, str, agi, ap, crit, hit, exp, haste, mastery, mh, oh, ranged, procs, gear_buffs, level=85):
        # This will need to be adjusted if at any point we want to support
        # other classes, but this is probably the easiest way to do it for
        # the moment.
        self.str = str
        self.agi = agi
        self.ap = ap
        self.crit = crit
        self.hit = hit
        self.exp = exp
        self.haste = haste
        self.mastery = mastery
        self.mh = mh
        self.oh = oh
        self.ranged = ranged
        self.procs = procs
        self.gear_buffs = gear_buffs
        self.level = level

    def _set_constants_for_level(self):
        try:
            self.melee_hit_rating_conversion = self.melee_hit_rating_conversion_values[self.level]
            self.spell_hit_rating_conversion = self.spell_hit_rating_conversion_values[self.level]
            self.crit_rating_conversion = self.crit_rating_conversion_values[self.level]
            self.haste_rating_conversion = self.haste_rating_conversion_values[self.level]
            self.expertise_rating_conversion = self.expertise_rating_conversion_values[self.level]
            self.mastery_rating_conversion = self.mastery_rating_conversion_values[self.level]
        except KeyError:
            raise exceptions.InvalidLevelException(_('No conversion factor available for level {level}').format(level=self.level))

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == 'level':
            self._set_constants_for_level()

    def get_mastery_from_rating(self, rating=None):
        if rating is None:
            rating = self.mastery
        return 8 + rating / self.mastery_rating_conversion

    def get_melee_hit_from_rating(self, rating=None):
        if rating is None:
            rating = self.hit
        return rating / (100 * self.melee_hit_rating_conversion)

    def get_expertise_from_rating(self, rating=None):
        if rating is None:
            rating = self.exp
        return rating / (100 * self.expertise_rating_conversion)

    def get_spell_hit_from_rating(self, rating=None):
        if rating is None:
            rating = self.hit
        return rating / (100 * self.spell_hit_rating_conversion)

    def get_crit_from_rating(self, rating=None):
        if rating is None:
            rating = self.crit
        return rating / (100 * self.crit_rating_conversion)

    def get_haste_multiplier_from_rating(self, rating=None):
        if rating is None:
            rating = self.haste
        return 1 + rating / (100 * self.haste_rating_conversion)

class Weapon(object):
    allowed_melee_enchants = proc_data.allowed_melee_enchants

    def __init__(self, damage, speed, weapon_type, enchant=None):
        self.speed = speed
        self.weapon_dps = damage * 1.0 / speed
        self.type = weapon_type

        if self.type == 'thrown':
            self._normalization_speed = 2.1
        elif self.type in ['gun', 'bow', 'crossbow']:
            self._normalization_speed = 2.8
        elif self.type in ['2h_sword', '2h_mace', '2h_axe', 'polearm']:
            self._normalization_speed = 3.3
        elif self.type == 'dagger':
            self._normalization_speed = 1.7
        else:
            self._normalization_speed = 2.4

        if enchant is not None:
            self.set_enchant(enchant)

    def set_enchant(self, enchant):
        if enchant == None:
            self.del_enchant()
        else:
            if self.is_melee():
                if enchant in self.allowed_melee_enchants:
                    self.del_enchant()
                    proc = procs.Proc(**self.allowed_melee_enchants[enchant])
                    setattr(self, enchant, proc)
                else:
                    raise exceptions.InvalidInputException(_('Enchant {enchant} is not allowed.').format(enchant=enchant))
            else:
                raise exceptions.InvalidInputException(_('Only melee weapons can be enchanted with {enchant}.').format(enchant=enchant))

    def del_enchant(self):
        for i in self.allowed_melee_enchants:
            if getattr(self, i):
                delattr(self, i)

    def __getattr__(self, name):
        # Any enchant we haven't assigned a value to, we don't have.
        if name in self.allowed_melee_enchants:
            return False
        object.__getattribute__(self, name)

    def is_melee(self):
        return not self.type in frozenset(['gun', 'bow', 'crossbow', 'thrown'])

    def damage(self, ap=0):
        return self.speed * (self.weapon_dps + ap / 14.)

    def normalized_damage(self, ap=0):
        return self.speed * self.weapon_dps + self._normalization_speed * ap / 14.

# Catch-all for non-proc gear based buffs (static or activated)
class GearBuffs(object):
    activated_boosts = {
        # Duration and cool down in seconds - name is mandatory for damage-on-use boosts
        'unsolvable_riddle':              {'stat': 'agi', 'value': 1605, 'duration': 20, 'cooldown': 120},
        'demon_panther':                  {'stat': 'agi', 'value': 1425, 'duration': 20, 'cooldown': 120},
        'skardyns_grace':                 {'stat': 'mastery', 'value': 1260, 'duration': 20, 'cooldown': 120},
        'heroic_skardyns_grace':          {'stat': 'mastery', 'value': 1425, 'duration': 20, 'cooldown': 120},
        'potion_of_the_tolvir':           {'stat': 'agi', 'value': 1200, 'duration': 25, 'cooldown': None}, #Cooldown = fight length
        'potion_of_the_tolvir_prepot':    {'stat': 'agi', 'value': 1200, 'duration': 23, 'cooldown': None}, #Very rough guesstimate; actual modeling should be done with the opener sequence, alas, there's no such thing.
        'engineer_glove_enchant':         {'stat': 'haste', 'value': 340, 'duration': 12, 'cooldown': 60},  #WotLK tinker
        'synapse_springs':                {'stat': 'varies', 'value': 480, 'duration': 10, 'cooldown': 60}, #Overwrite stat in the model for the highest of agi, str, int
        'tazik_shocker':                  {'stat': 'spell_damage', 'value': 4800, 'duration': 0, 'cooldown': 60, 'name': 'Tazik Shocker'},
        'lifeblood':                      {'stat': 'haste', 'value': 480, 'duration': 20, 'cooldown': 120},
        'ancient_petrified_seed':         {'stat': 'agi', 'value': 1277, 'duration': 15, 'cooldown': 60},
        'heroic_ancient_petrified_seed':  {'stat': 'agi', 'value': 1441, 'duration': 15, 'cooldown': 60},
        'rickets_magnetic_fireball':      {'stat': 'crit', 'value': 1700, 'duration': 20, 'cooldown': 120},
        'kiroptyric_sigil':               {'stat': 'agi', 'value': 2290, 'duration': 15, 'cooldown': 90},
        'heroic_kiroptyric_sigil':        {'stat': 'agi', 'value': 2585, 'duration': 15, 'cooldown': 90},  #Not available in-game
        'lfr_kiroptyric_sigil':           {'stat': 'agi', 'value': 2029, 'duration': 15, 'cooldown': 90},  #Not available in-game
    }

    other_gear_buffs = [
        'leather_specialization',       # Increase %stat by 5%
        'chaotic_metagem',              # Increase critical damage by 3%
        'rogue_t11_2pc',                # Increase crit chance for BS, Mut, SS by 5%
        'rogue_t12_2pc',                # Add 6% of melee crit damage as a fire DOT
        'rogue_t12_4pc',                # Increase crit/haste/mastery rating by 25% every TotT
        'rogue_t13_2pc',                # Decrease energy cost by 20% for 6secs every TotT
        'rogue_t13_4pc',                # ShD +2secs, AR +3secs, Vendetta +9secs
        'rogue_t13_legendary',          # Increase 45% damage on SS and RvS, used in case the rogue only equips the mh of a set.
        'mixology',
        'master_of_anatomy'
    ]

    allowed_buffs = frozenset(other_gear_buffs + activated_boosts.keys())

    def __init__(self, *args):
        for arg in args:
            if arg in self.allowed_buffs:
                setattr(self, arg, True)

    def __getattr__(self, name):
        # Any gear buff we haven't assigned a value to, we don't have.
        if name in self.allowed_buffs:
            return False
        object.__getattribute__(self, name)

    def metagem_crit_multiplier(self):
        if self.chaotic_metagem:
            return 1.03
        else:
            return 1

    def rogue_t11_2pc_crit_bonus(self):
        if self.rogue_t11_2pc:
            return .05
        else:
            return 0

    def rogue_t12_2pc_damage_bonus(self):
        if self.rogue_t12_2pc:
            return .06
        else:
            return 0

    def rogue_t12_4pc_stat_bonus(self):
        if self.rogue_t12_4pc:
            return .25
        else:
            return 0

    def rogue_t13_2pc_cost_multiplier(self):
        if self.rogue_t13_2pc:
            return 1 / 1.05
        else:
            return 1

    def leather_specialization_multiplier(self):
        if self.leather_specialization:
            return 1.05
        else:
            return 1

    def get_all_activated_agi_boosts(self):
        return self.get_all_activated_boosts_for_stat('agi')

    def get_all_activated_boosts_for_stat(self, stat=None):
        boosts = []
        for boost in GearBuffs.activated_boosts:
            if getattr(self, boost) and (stat is None or GearBuffs.activated_boosts[boost]['stat'] == stat):
                boosts.append(GearBuffs.activated_boosts[boost])

        return boosts

    def get_all_activated_boosts(self):
        return self.get_all_activated_boosts_for_stat()

    #This is haste rating because the conversion to haste requires a level.
    #Too, if reported as a haste value, it must be added to the value from other rating correctly.
    #This does too, but reinforces the fact that it's rating.
    def get_all_activated_haste_rating_boosts(self):
        return self.get_all_activated_boosts_for_stat('haste')
