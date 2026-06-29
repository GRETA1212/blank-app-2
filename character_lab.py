from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_AUDIO_BYTES = 30 * 1024 * 1024

REFERENCE_SLOTS = (
    "front_neutral",
    "front_smile",
    "three_quarter_left",
    "three_quarter_right",
    "left_profile",
    "right_profile",
    "full_body",
    "speaking",
    "surprised",
    "worried",
)


@dataclass
class VoiceDNA:
    primary_language: str
    secondary_languages: list[str]
    accent: str
    pitch: str
    words_per_minute: int
    energy: str
    pause_style: str
    emotional_range: list[str]
    pronunciation_notes: list[str] = field(default_factory=list)
    provider: str = "Not configured"
    provider_voice_id: str = ""
    consent_status: str = "Use only a licensed synthetic voice or a consenting actor"


@dataclass
class AppearanceDNA:
    apparent_age: int
    skin_tone: str
    eye_color: str
    face_shape: str
    hair: str
    distinguishing_features: list[str]
    body_and_posture: str
    signature_item: str
    color_palette: list[str]
    realism_notes: list[str]


@dataclass
class BehaviorDNA:
    personality: list[str]
    gestures: list[str]
    habits: list[str]
    expertise: list[str]
    boundaries: list[str]
    catchphrase: str


@dataclass
class CharacterDNA:
    name: str
    niche: str
    role: str
    appearance: AppearanceDNA
    voice: VoiceDNA
    behavior: BehaviorDNA
    wardrobe: list[dict[str, str]]
    locations: list[dict[str, str]]
    actions: list[dict[str, str]]
    camera_rules: list[str]
    continuity_rules: list[str]
    negative_prompt: list[str]
    version: int = 1


DEFAULT_CHARACTER_DNA: dict[str, CharacterDNA] = {
    "Sofia": CharacterDNA(
        name="Sofia",
        niche="Beauty",
        role="Virtual makeup creator",
        appearance=AppearanceDNA(
            apparent_age=26,
            skin_tone="Warm olive with natural skin texture",
            eye_color="Hazel-brown",
            face_shape="Soft oval with slight natural asymmetry",
            hair="Long chestnut-brown hair with soft face-framing layers",
            distinguishing_features=[
                "Small beauty mark near the left cheek",
                "Medium natural eyebrows",
                "Small gold hoop earrings",
            ],
            body_and_posture="Average build, relaxed upright posture, precise hand movements",
            signature_item="Small gold hoop earrings",
            color_palette=["cream", "blush pink", "warm beige", "soft brown"],
            realism_notes=[
                "Keep pores and light skin texture visible",
                "Avoid plastic skin and perfectly symmetrical facial features",
                "Maintain the same eye spacing, nose shape and jawline in every scene",
            ],
        ),
        voice=VoiceDNA(
            primary_language="Italian",
            secondary_languages=["English"],
            accent="Natural Northern/Central Italian, neutral enough for broad comprehension",
            pitch="Medium-high, warm",
            words_per_minute=158,
            energy="Friendly and energetic without sounding rushed",
            pause_style="Short pause before the reveal; slower on technical steps",
            emotional_range=["neutral", "encouraging", "excited", "mildly surprised", "honest disappointment"],
            pronunciation_notes=["Clearly pronounce product names", "Do not exaggerate English words"],
        ),
        behavior=BehaviorDNA(
            personality=["warm", "precise", "confident", "practical", "honest"],
            gestures=[
                "Checks the mirror before turning to camera",
                "Raises one eyebrow when identifying a mistake",
                "Rotates products slowly so the label can be seen",
                "Uses small controlled brush movements",
            ],
            habits=[
                "Compares both sides of the face",
                "Shows the result in natural light",
                "Admits when a trend does not work",
            ],
            expertise=["makeup application", "color matching", "beauty product demonstrations", "before-and-after teaching"],
            boundaries=[
                "Never makes medical claims",
                "Never guarantees a product result",
                "Never presents an undisclosed advertisement as an independent review",
            ],
            catchphrase="Small change, completely different result.",
        ),
        wardrobe=[
            {"name": "Studio neutral", "description": "Cream fitted knit top, gold hoops, soft natural makeup"},
            {"name": "Soft glam", "description": "Blush-pink blouse, gold hoops, polished evening makeup"},
            {"name": "Product test", "description": "Warm beige shirt, hair tied back, minimal base makeup"},
        ],
        locations=[
            {"name": "Sofia beauty studio", "description": "Cream walls, round illuminated mirror, daylight, organized product shelf"},
            {"name": "Window test corner", "description": "Natural side light, neutral wall, close-up friendly"},
            {"name": "Evening vanity", "description": "Warm practical lights, darker background, premium but believable"},
        ],
        actions=[
            {"name": "Apply product", "description": "Pick up product, show it, apply slowly, check mirror, react"},
            {"name": "Before and after", "description": "Match camera position and lighting, reveal both sides clearly"},
            {"name": "Trend test", "description": "Explain the claim, test one variable, show honest result"},
            {"name": "Correction tutorial", "description": "Show mistake, explain cause, correct it, compare"},
        ],
        camera_rules=[
            "Use close-up for technique and medium shot for reactions",
            "Maintain realistic eye line between mirror and camera",
            "Avoid beauty filters that change facial geometry",
            "Keep lighting direction consistent within a tutorial",
        ],
        continuity_rules=[
            "Hazel-brown eyes never change color",
            "Chestnut layered hair remains the same length unless an episode explicitly changes it",
            "Gold hoop earrings appear in standard studio episodes",
            "Beauty mark stays on the left cheek",
        ],
        negative_prompt=[
            "plastic skin",
            "face morphing",
            "different eye color",
            "extra fingers",
            "warped makeup brush",
            "floating product",
            "unreadable product text",
            "celebrity likeness",
        ],
    ),
    "Elena": CharacterDNA(
        name="Elena",
        niche="Real Estate",
        role="Virtual property presenter",
        appearance=AppearanceDNA(
            apparent_age=31,
            skin_tone="Light-medium neutral complexion with natural texture",
            eye_color="Dark brown",
            face_shape="Defined oval",
            hair="Straight dark-brunette bob ending below the jaw",
            distinguishing_features=["Minimal jewelry", "Slim steel watch", "Confident direct gaze"],
            body_and_posture="Tall-appearing posture, controlled walking pace, professional hand gestures",
            signature_item="Slim steel watch and dark tablet",
            color_palette=["stone", "navy", "white", "charcoal"],
            realism_notes=[
                "Professional, credible appearance rather than fashion-model styling",
                "Keep bob length and center part stable",
                "Maintain realistic proportions when walking through rooms",
            ],
        ),
        voice=VoiceDNA(
            primary_language="Italian",
            secondary_languages=["English", "Albanian"],
            accent="Clear neutral Italian presenter accent",
            pitch="Medium-low",
            words_per_minute=134,
            energy="Calm, informed and commercially confident",
            pause_style="Pause before price, area, defects and the main reveal",
            emotional_range=["neutral", "impressed", "skeptical", "cautious", "confident"],
            pronunciation_notes=["Read dimensions slowly", "Pronounce currency and property terminology precisely"],
        ),
        behavior=BehaviorDNA(
            personality=["elegant", "curious", "trustworthy", "observant", "commercially aware"],
            gestures=[
                "Opens doors and cupboards before describing them",
                "Points to architectural details with an open hand",
                "Uses a tablet to show a floor plan",
                "Looks out of the window before discussing orientation",
            ],
            habits=[
                "Checks natural light",
                "Mentions one advantage and one limitation",
                "Measures or verifies rather than guessing",
            ],
            expertise=["property presentation", "layout analysis", "buyer questions", "listing videos"],
            boundaries=[
                "Never invents prices, dimensions or legal status",
                "Clearly labels concept properties",
                "Uses real listing media only with permission",
            ],
            catchphrase="The detail that changes this entire property is here.",
        ),
        wardrobe=[
            {"name": "City apartment", "description": "Stone blazer, white top, tailored charcoal trousers, steel watch"},
            {"name": "Luxury listing", "description": "Navy suit, cream blouse, discreet jewelry"},
            {"name": "Construction visit", "description": "White shirt, dark trousers, safety vest and helmet where required"},
        ],
        locations=[
            {"name": "Modern apartment", "description": "Natural daylight, clean contemporary finishes, realistic city view"},
            {"name": "Compact city flat", "description": "Narrow rooms, storage challenges, believable furniture scale"},
            {"name": "Property office", "description": "Desk, floor-plan display, neutral branded wall"},
            {"name": "Construction site", "description": "Safe marked route, unfinished walls, PPE, realistic ambient sound"},
        ],
        actions=[
            {"name": "Guided tour", "description": "Enter, orient viewer, show three key spaces, reveal benefit or issue"},
            {"name": "Floor-plan explanation", "description": "Hold tablet, highlight circulation, compare room relationships"},
            {"name": "Storage test", "description": "Open storage, show depth, check obstruction and usable volume"},
            {"name": "Light and view test", "description": "Open curtains, show orientation, explain time-of-day impact"},
        ],
        camera_rules=[
            "Use wide lens carefully; do not distort room size",
            "Show transitions between rooms so layout remains understandable",
            "Use detail shots only after establishing the room",
            "Keep vertical lines straight in architectural shots",
        ],
        continuity_rules=[
            "Dark-brunette bob and steel watch remain consistent",
            "Tablet design and case remain the same",
            "Numbers spoken must match captions and metadata",
            "The same property must keep identical doors, windows and finishes across scenes",
        ],
        negative_prompt=[
            "impossible architecture",
            "changing window positions",
            "warped doors",
            "oversized furniture",
            "fake city landmarks",
            "unverified price",
            "celebrity likeness",
        ],
    ),
    "Luna": CharacterDNA(
        name="Luna",
        niche="Mini Movies",
        role="Lead character in an episodic mystery universe",
        appearance=AppearanceDNA(
            apparent_age=24,
            skin_tone="Light olive with natural texture",
            eye_color="Amber-brown",
            face_shape="Heart-shaped with a soft jaw",
            hair="Shoulder-length black wavy hair",
            distinguishing_features=["Silver crescent pendant", "Expressive eyebrows", "Small scar near right wrist"],
            body_and_posture="Slim average build; cautious posture under stress and decisive posture during confrontation",
            signature_item="Silver crescent pendant",
            color_palette=["midnight blue", "charcoal", "silver", "muted cream"],
            realism_notes=[
                "Facial emotion should appear before dialogue",
                "Keep pendant scale and shape identical",
                "Avoid glamour retouching during danger or emotional scenes",
            ],
        ),
        voice=VoiceDNA(
            primary_language="English",
            secondary_languages=["Italian"],
            accent="Soft international English with a subtle European character",
            pitch="Medium-low and intimate",
            words_per_minute=118,
            energy="Controlled, emotionally present, breathier under danger",
            pause_style="Longer pause before secrets and after impossible discoveries",
            emotional_range=["neutral", "suspicious", "frightened", "angry", "sad", "determined", "whispering"],
            pronunciation_notes=["Keep names consistent across episodes", "Do not overperform fear"],
        ),
        behavior=BehaviorDNA(
            personality=["intelligent", "emotionally brave", "mysterious", "imperfect", "loyal"],
            gestures=[
                "Touches the pendant when anxious",
                "Looks over her shoulder before answering a secret call",
                "Processes information silently before speaking",
                "Takes one step backward when she recognizes danger",
            ],
            habits=[
                "Saves evidence instead of deleting it",
                "Notices small inconsistencies",
                "Asks direct questions even when afraid",
            ],
            expertise=["pattern recognition", "basic digital investigation", "reading people"],
            boundaries=[
                "Never becomes suddenly omniscient",
                "Never forgets established relationships or past events",
                "Never resolves a major mystery without earned evidence",
            ],
            catchphrase="Tomorrow already knows what I decide tonight.",
        ),
        wardrobe=[
            {"name": "Core outfit", "description": "Dark-blue coat, muted cream knit, charcoal trousers, crescent pendant"},
            {"name": "Apartment night", "description": "Charcoal lounge top, dark trousers, pendant"},
            {"name": "Future office", "description": "Minimal midnight-blue jacket, silver details, pendant"},
        ],
        locations=[
            {"name": "Luna apartment", "description": "Small modern apartment, rain-streaked window, warm lamp, recurring hallway"},
            {"name": "Dim corridor", "description": "Long concrete corridor, intermittent practical lights, numbered doors"},
            {"name": "Empty café", "description": "Closed café after hours, blue street light, one red booth"},
            {"name": "Rooftop", "description": "City night, wind, low safety wall, distant antennas"},
            {"name": "Train station", "description": "Late-night platform, sparse passengers, analog clock"},
        ],
        actions=[
            {"name": "Receive impossible message", "description": "Phone vibrates, Luna reads, freezes, checks timestamp, looks toward sound"},
            {"name": "Investigate evidence", "description": "Photograph clue, compare dates, notice mismatch, hide evidence"},
            {"name": "Danger reaction", "description": "Hear sound, control breath, move quietly, choose cover"},
            {"name": "Confrontation", "description": "Hold eye contact, ask direct question, react before replying"},
            {"name": "Run and hide", "description": "Short believable sprint, use environment, recover breath"},
        ],
        camera_rules=[
            "Use close-ups for emotional realization and wider shots for spatial danger",
            "Motivated handheld movement only during uncertainty or pursuit",
            "Maintain screen direction across cuts",
            "Use recurring visual motifs: pendant, phone timestamp and corridor light",
        ],
        continuity_rules=[
            "Amber-brown eyes, black wavy hair and crescent pendant never change",
            "Luna remembers all previous episode events",
            "Injuries, objects and messages persist until resolved",
            "Recurring locations keep stable geography",
            "Episode timestamps and phone content must remain logically consistent",
        ],
        negative_prompt=[
            "different pendant",
            "changing hairstyle",
            "face morphing",
            "extra fingers",
            "unreadable phone screen",
            "impossible room geography",
            "overly glamorous fear",
            "celebrity likeness",
        ],
    ),
}


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "character"


def character_to_dict(character: CharacterDNA) -> dict[str, Any]:
    return asdict(character)


def character_from_dict(data: dict[str, Any]) -> CharacterDNA:
    return CharacterDNA(
        name=data["name"],
        niche=data["niche"],
        role=data["role"],
        appearance=AppearanceDNA(**data["appearance"]),
        voice=VoiceDNA(**data["voice"]),
        behavior=BehaviorDNA(**data["behavior"]),
        wardrobe=list(data.get("wardrobe", [])),
        locations=list(data.get("locations", [])),
        actions=list(data.get("actions", [])),
        camera_rules=list(data.get("camera_rules", [])),
        continuity_rules=list(data.get("continuity_rules", [])),
        negative_prompt=list(data.get("negative_prompt", [])),
        version=int(data.get("version", 1)),
    )


def clone_default_character(name: str) -> CharacterDNA:
    if name not in DEFAULT_CHARACTER_DNA:
        raise KeyError(f"Unknown default character: {name}")
    return character_from_dict(deepcopy(character_to_dict(DEFAULT_CHARACTER_DNA[name])))


def character_directory(name: str, storage_root: Path | str = "storage") -> Path:
    return Path(storage_root) / "characters" / slugify(name)


def save_character(character: CharacterDNA, storage_root: Path | str = "storage") -> Path:
    folder = character_directory(character.name, storage_root)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / "profile.json"
    temporary = folder / "profile.json.tmp"
    temporary.write_text(
        json.dumps(character_to_dict(character), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_character(name: str, storage_root: Path | str = "storage") -> CharacterDNA:
    profile_path = character_directory(name, storage_root) / "profile.json"
    if profile_path.exists():
        return character_from_dict(json.loads(profile_path.read_text(encoding="utf-8")))
    return clone_default_character(name)


def safe_filename(filename: str) -> str:
    raw_name = Path(filename).name
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(raw_name).stem).strip("-") or "asset"
    suffix = Path(raw_name).suffix.lower()
    return f"{stem}{suffix}"


def validate_asset(filename: str, payload: bytes, asset_kind: str) -> None:
    suffix = Path(filename).suffix.lower()
    if asset_kind == "reference_image":
        if suffix not in IMAGE_EXTENSIONS:
            raise ValueError("Reference images must be PNG, JPG, JPEG or WEBP.")
        if len(payload) > MAX_IMAGE_BYTES:
            raise ValueError("Reference image exceeds the 15 MB limit.")
    elif asset_kind == "voice_sample":
        if suffix not in AUDIO_EXTENSIONS:
            raise ValueError("Voice samples must be MP3, WAV, M4A or AAC.")
        if len(payload) > MAX_AUDIO_BYTES:
            raise ValueError("Voice sample exceeds the 30 MB limit.")
    else:
        raise ValueError(f"Unsupported asset kind: {asset_kind}")
    if not payload:
        raise ValueError("The uploaded asset is empty.")


def save_asset(
    character_name: str,
    asset_kind: str,
    filename: str,
    payload: bytes,
    *,
    slot: str | None = None,
    storage_root: Path | str = "storage",
) -> Path:
    validate_asset(filename, payload, asset_kind)
    if asset_kind == "reference_image":
        safe_slot = slugify(slot or "unassigned")
        folder = character_directory(character_name, storage_root) / "references" / safe_slot
    else:
        folder = character_directory(character_name, storage_root) / "voice"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / safe_filename(filename)
    destination.write_bytes(payload)
    return destination


def list_assets(character_name: str, storage_root: Path | str = "storage") -> list[dict[str, Any]]:
    root = character_directory(character_name, storage_root)
    if not root.exists():
        return []
    assets: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "profile.json" and not path.name.endswith(".tmp"):
            assets.append(
                {
                    "name": path.name,
                    "relative_path": str(path.relative_to(root)),
                    "size_bytes": path.stat().st_size,
                    "extension": path.suffix.lower(),
                }
            )
    return assets


def build_scene_direction(
    character: CharacterDNA,
    *,
    dialogue: str,
    emotion: str,
    action_name: str,
    location_name: str,
    wardrobe_name: str,
    camera: str,
    duration_seconds: float,
) -> dict[str, Any]:
    action = next((item for item in character.actions if item["name"] == action_name), None)
    location = next((item for item in character.locations if item["name"] == location_name), None)
    wardrobe = next((item for item in character.wardrobe if item["name"] == wardrobe_name), None)
    if action is None:
        raise ValueError(f"Unknown action for {character.name}: {action_name}")
    if location is None:
        raise ValueError(f"Unknown location for {character.name}: {location_name}")
    if wardrobe is None:
        raise ValueError(f"Unknown wardrobe for {character.name}: {wardrobe_name}")
    if duration_seconds <= 0 or duration_seconds > 30:
        raise ValueError("A scene duration must be greater than 0 and no more than 30 seconds.")

    appearance = character.appearance
    visual_prompt = (
        f"Photorealistic recurring virtual character {character.name}, apparent age {appearance.apparent_age}, "
        f"{appearance.skin_tone}, {appearance.eye_color} eyes, {appearance.face_shape} face, {appearance.hair}. "
        f"Distinguishing identity: {', '.join(appearance.distinguishing_features)}. "
        f"Signature item: {appearance.signature_item}. Wardrobe: {wardrobe['description']}. "
        f"Location: {location['description']}. Action: {action['description']}. "
        f"Emotion: {emotion}. Camera: {camera}. Vertical 9:16 cinematic frame, natural anatomy, "
        "consistent identity, realistic skin texture, believable lighting and physical interaction."
    )
    performance_direction = (
        f"{character.name} performs: {action['description']} Emotion is {emotion}. "
        f"Use these characteristic gestures where natural: {', '.join(character.behavior.gestures[:2])}. "
        "Let the facial reaction begin slightly before the spoken line. Include natural blinking, breathing "
        "and brief eye-line changes; do not stare continuously into the lens."
    )
    voice_direction = (
        f"Voice: {character.voice.pitch}; {character.voice.energy}. "
        f"Target {character.voice.words_per_minute} words per minute. Accent: {character.voice.accent}. "
        f"Emotion: {emotion}. Pause style: {character.voice.pause_style}. "
        f"Dialogue: {dialogue}"
    )
    continuity_checks = [
        f"Eye color remains {appearance.eye_color}.",
        f"Hair remains: {appearance.hair}.",
        f"Signature item remains visible when physically appropriate: {appearance.signature_item}.",
        f"Wardrobe matches '{wardrobe['name']}'.",
        f"Location geometry matches '{location['name']}' in adjacent scenes.",
        *character.continuity_rules,
    ]
    return {
        "character": character.name,
        "duration_seconds": duration_seconds,
        "dialogue": dialogue,
        "emotion": emotion,
        "action": action,
        "location": location,
        "wardrobe": wardrobe,
        "camera": camera,
        "visual_prompt": visual_prompt,
        "negative_prompt": ", ".join(character.negative_prompt),
        "performance_direction": performance_direction,
        "voice_direction": voice_direction,
        "continuity_checks": continuity_checks,
        "safety_and_rights": [
            character.voice.consent_status,
            "Do not imitate a real person or celebrity.",
            "Use licensed music, media and voice services.",
            "Label realistic AI-generated media where the platform requires it.",
        ],
    }


def calculate_consistency_score(checks: dict[str, bool]) -> dict[str, Any]:
    if not checks:
        return {"score": 0.0, "passed": 0, "total": 0, "status": "No checks recorded"}
    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    score = round(passed / total * 100, 1)
    if score == 100:
        status = "APPROVED"
    elif score >= 80:
        status = "FIX MINOR ISSUES"
    else:
        status = "REJECT AND REGENERATE"
    return {"score": score, "passed": passed, "total": total, "status": status}
