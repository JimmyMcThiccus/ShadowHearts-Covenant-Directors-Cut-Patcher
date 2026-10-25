# English for the Director's Cut Nahash Temple scripts (KS_*), keyed by data-segment offset of the Japanese string.
# Plain sentences are wrapped to 40 columns x 3 lines by apply_tr.py; "$" forces a break.  "%t0%p4Name" = speaker plate.

TEAMS = {  # debug-map party presets (SetLocationName); shared by KS_00_U and KS_10_U
    0x0c20: "Second Expedition", 0x0c2d: "The Fugitives", 0x0c38: "Code of the Lone Wolf",
    0x0c41: "The Princess's Party", 0x0c4e: "Just the Two of Us", 0x0c57: "Bodyguard & White Wolf",
    0x0c64: "Team Kurando", 0x0c71: "Team Yuri", 0x0c7e: "Ouka Startup Test", 0x0c8b: "The Odd Couple",
    0x0c96: "Everyone Together!", 0x0ca1: "The Ascetics", 0x0cac: "The Puppeteer",
    0x0cb5: "The Wandering Dancer", 0x0cc0: "The SG Trio", 0x0d59: "Challenger",
}
LIB = {  # shared field-library strings (item pickups etc.); appended after the highlighted item name
    0x0048: " Crest obtained!", 0x0062: " Card obtained!", 0x0079: " obtained!", 0x0028: " ",
    0x0088: "It's empty.", 0x009b: "It can't be opened from behind.", 0x02d7: "HP and MP fully restored!",
}
LENNY, NICOLAI, VERONICA = "%t0%p4Lenny", "%t0%p4Nicolai", "%t0%p4Veronica"

KS = {
"KS_00_U": {**TEAMS,
    0x0e1f: "Hey, hey! You're just gonna bail on the mission and go home?!",
    0x0e4b: LENNY,
    0x0e56: "Huh? This door won't open?!",
    0x0e77: NICOLAI,
    0x0e84: "Ah, I forgot to mention. The doors in this temple open with a pair of switches on the same floor.",
    0x0eec: "What a pain in the ass... Then let's hurry up and go hit these switches of yours.",
    0x0fc4: "Well, here we are. This is the undersea temple the Master spoke of.",
    0x1001: "All right! Let's get this investigation rolling!",
    0x1024: VERONICA,
    0x1033: "Oh, calm down, will you? We've been walking since morning. I'm exhausted.",
    0x107e: "How the hell am I supposed to calm down?! Every guy who went missing down here was one of my men!",
    0x10d5: "Charge in without thinking and you'll get lost down here forever. Especially with a brain like yours.",
    0x113e: "Why, you...!!",
    0x1153: "That's enough, both of you!",
    0x1170: "We must finish our survey before they bring the Emigre Manuscript here. We have no time for idle chatter.",
    0x11d7: "...Tch! Fine, fine!",
    0x11ee: "Phew... Looks like some lowly monsters have started prowling around here.",
    0x122a: "Did these things get my men?",
    0x1258: "No. I doubt your men would fall to small fry like these. Unless something far stronger lurks here...",
    0x12b3: "Hey. What's this switch?",
    0x12d3: "See the door over there? This switch is what opens it.",
    0x1309: "It seems that door won't open unless both switches on this floor are thrown.",
    0x135c: "What a pain in the ass... Then let's hurry up and go hit the other one too.",
},
"KS_01_U": {**LIB,
    0x0c38: "%t0%p4Clawed Medic",
    0x0c49: "Are you hurt? Are you tired? If so, leave it to me, the Clawed Medic!",
    0x0c9e: "I'll keep watch here. If you need anything, just call on me!",
    0x0dad: LENNY,
    0x0db8: "What the hell! Another door that won't open?!",
    0x0dda: NICOLAI,
    0x0de7: "This gate only works one way. See the arrow drawn on the floor?",
    0x0e27: "It can only be opened from the side the arrow points from.",
    0x0e7e: "Whoa, cool. An automatic door!",
    0x0e9c: "It's not quite as convenient as that...",
    0x0ec4: "Whoa! H-hey! We're locked in?!",
    0x0ef2: VERONICA,
    0x0f01: "Don't lose your head! This gate only goes one way. Look, there's an arrow on the floor, see?",
    0x0f56: "It only opens from the side the arrow points from. Get it?",
    0x0f8d: "Oh... So that's how it works... Don't scare me like that! Geez!",
},
"KS_02_U": {**LIB},
"KS_03_U": {**LIB,
    0x0d64: LENNY,
    0x0d6f: "Man, I still can't believe it. A temple at the bottom of the sea...",
    0x0db9: VERONICA,
    0x0dc8: "Oh, that's right. This is your first time here, isn't it?",
    0x0e02: NICOLAI,
    0x0e0f: "Long ago, they say, followers of a heretic cult built their temples in hidden places to escape persecution...",
    0x0e6a: "This temple must be one of those ruins.",
    0x0e9a: "Huh... But for a place on the sea floor, there's air, and no water's getting in.",
    0x0ee4: "Some power must be at work here. The Master ordered this survey because he's interested in its source.",
    0x0f4b: "Oh? But wasn't it you who suggested this survey to the Master in the first place?",
    0x0f9e: "And I've been paying for it. Still no results, and now this mess on top of it.",
    0x0ff1: "Hmm...",
    0x0ffa: "These stairs...?",
    0x1009: "When I came here before, there wasn't a floor below this one...",
    0x103d: "We may have struck gold.",
},
"KS_10_U": {**TEAMS,
    0x0de5: LENNY,
    0x0df0: "Wh-what the...?! You did this?!",
    0x0e1e: NICOLAI,
    0x0e2b: "No doubt about it... And it doesn't seem inclined to let us leave in one piece either.",
    0x0e74: VERONICA,
    0x0e83: "Fine by me. Naughty children need a good, long punishment!",
    0x0ecd: "Damn... That was one hell of a monster!",
    0x0eff: "So, what are you going to do, Nicolai?",
    0x0f1e: "...Once we have the Emigre Manuscript, I'll report to the Master myself. I'll recommend we end the survey.",
    0x0f81: "Damn right! I'm not losing any more of my men down here for nothing!",
    0x0fca: "The Master won't be pleased... You'd better be ready for that.",
    0x1018: "The Master's displeasure, hm... It may restrict my movements a little, but it can't be helped.",
    0x105f: "With this ring, once the pact is sealed... I can surpass that man...",
},
}

# KS_00_U opening caption: the typewriter routine appends one argument at a time, so each slot holds a chunk.
# Keyed by the 0x15 operand's code offset (several kana share one data string, so the key is per site).
def _chunks(text, slots, n=3):
    """The typewriter types ~1 char per frame and waits only 70 ms per slot, so a slot longer than ~4 chars is still
    typing when the next arrives and the rest of the line is lost (seen live 2026-10-24).  Split into <= n chars."""
    parts = [text[i:i+n] for i in range(0, len(text), n)]
    assert len(parts) <= slots, (text, len(parts), slots)
    return parts + [""] * (slots - len(parts))

CAPTION_LINES = [
    _chunks("Hours before Yuri reached Cannes", 12),       # ウルがカンヌに入る数刻前
    _chunks("Ruins beneath the Mediterranean", 12),        # 地中海南部の底に沈む遺跡
    _chunks("  - Temple of Nahash -", 10),                 # 　―ナハシュ神殿―
]
CAPTION_WIDTH = 20   # columns of the caption windows (x 150 + 20*17 px = 490 < 512)
