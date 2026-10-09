"""Bind reviewed encounter geometry to the current request and staged chunks.

This is a staging gate, not evidence that a boss runs or its tactics are handled.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANDBOX = HERE.parents[2] / "tools/raid-lab/private/native-player-20261008a"
COMMON = HERE / "mechanics-geometry-source-v2.json"
COMMON_SHA = "fabe414859d5ed3d7486b3ab6b2bc979847c01fa56c793b0832f2c35e33bf2fc"
CLIENT_SHA = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"
REVIEWED = {
    "anomaly-mirror-container": ("mirror-geometry-source.json",
        "d1c334def34ae73ed4344c4f79e1f00431f35df49e1fc7eefc562b0c1095f306"),
    "anomaly-ultra": ("profile-assets/anomaly-ultra-hd-geometry-source.json",
        "39049233dbf1bed5b98145c214791e59a59f1c3d7707a260233bec144723f77c"),
    "special-chatterbox": ("profile-assets/special-chatterbox-hd-geometry-source.json",
        "b91fcdccf7b7c229e091cadb6a4acea6810aca31b81d8ec042953cb5b106c63b"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_profile_geometry(source, profile, common):
    """Reject a wrong encounter or changed shared hierarchy before native loading."""
    wave = source.get("wave_current_row") or source.get("current_rows", {}).get("wave", {})
    bound = source.get("profile", {})
    origin = source.get("source", {})
    role = bound.get("background_role")
    if (source.get("installed_client_sha256") != CLIENT_SHA or
            bound.get("id") != profile["productId"] or
            bound.get("wave_id") != profile["encounter"]["waveId"] or
            origin.get("common_geometry_sha256") != COMMON_SHA or
            wave.get("StageId") != profile["encounter"]["waveId"] or
            wave.get("BackgroundName") != profile["wave"]["backgroundKey"] or
            wave.get("TargetList") != profile["wave"]["targetMonsterIds"] or
            source.get("bundles", {}).get(role, {}).get("catalog_key") != profile["wave"]["backgroundKey"]):
        raise ValueError("Encounter geometry/profile/common-source mismatch")
    if any(source.get("bundles", {}).get(key) != value for key, value in common["bundles"].items()):
        raise ValueError("Shared original mechanical hierarchy changed")
    if not source.get("ready_for_chunk_staging") or source.get("unavailable_bundles"):
        raise ValueError("Encounter source dependency closure is incomplete")


def validate_staged_chunks(source, receipt):
    """Require every manifest chunk in the preserved sparse-store receipt.

    The private host separately checks actual staged bytes. Additional dynamic
    resources discovered by native runs remain a separate source-bound receipt.
    """
    if receipt.get("status") != "source_verified_sparse_chunks" or receipt.get("index_sha256") != source["index_sha256"]:
        raise ValueError("Staged source index differs")
    chunks = {row["hash"]: row for row in receipt["chunks"]}
    for name, bundle in source["verified_bundles"].items():
        expected = [row["hash"] for row in bundle["chunks"]]
        if set(receipt["bundles"].get(name, [])) != set(expected):
            raise ValueError("Encounter dependency bundle has not been staged: " + name)
        for row in bundle["chunks"]:
            actual = chunks.get(row["hash"], {})
            if any(actual.get(key) != row[key] for key in
                   ("store_offset", "compressed_bytes", "compressed_sha256", "decoded_bytes")):
                raise ValueError("Encounter staged chunk differs: " + row["hash"])


def geometry_source_for_profile(profile, require_staged=True):
    if sha(COMMON) != COMMON_SHA:
        raise ValueError("Common original geometry receipt changed")
    if profile is None or profile["productId"] == "anomaly-kraken":
        return COMMON
    entry = REVIEWED.get(profile["productId"])
    if entry is None:
        raise ValueError("Registered encounter still needs reviewed mechanical asset staging")
    path = HERE / entry[0]
    if sha(path) != entry[1]:
        raise ValueError("Reviewed encounter geometry source changed")
    source = json.loads(path.read_text(encoding="utf-8"))
    common = json.loads(COMMON.read_text(encoding="utf-8"))
    validate_profile_geometry(source, profile, common)
    if require_staged:
        receipt = json.loads((SANDBOX / "resource-chunks.json").read_text(encoding="utf-8"))
        validate_staged_chunks(source, receipt)
        if profile["productId"] == "anomaly-mirror-container":
            dynamic = HERE / "mirror-dynamic-effect-source.json"
            if sha(dynamic) != "56921c39ca86da7282625a15aa064917346e5224a5bdca7b25a1c262bb7015b0":
                raise ValueError("Mirror observed dynamic dependency source changed")
            validate_staged_chunks(json.loads(dynamic.read_text(encoding="utf-8")), receipt)
            closure = HERE / "mirror-monster-mechanical-resource-closure.json"
            if sha(closure) != "df89d8debf03facb7a45b1de051709ac12a954dee6947c009f24285c861830ad":
                raise ValueError("Mirror original monster mechanical resource closure changed")
            validate_staged_chunks(json.loads(closure.read_text(encoding="utf-8")), receipt)
            defaults = HERE / "mirror-default-spotskill-source.json"
            if sha(defaults) != "8e8ab151f8390e7b765ec951014eb816e2248c8b8feb0966d016dbcfb3ac84b3":
                raise ValueError("Mirror observed default skill sources changed")
            validate_staged_chunks(json.loads(defaults.read_text(encoding="utf-8")), receipt)
        elif profile["productId"] == "anomaly-ultra":
            closure = HERE / "profile-assets/ultra-monster-mechanical-resource-closure.json"
            if sha(closure) != "01dbc25da6530e86d612eb8a3a168545e2bc9e959170f7a90f3139a202d9de9c":
                raise ValueError("Ultra original monster resource source changed")
            validate_staged_chunks(json.loads(closure.read_text(encoding="utf-8")), receipt)
            effect = HERE / "profile-assets/ultra-purple-death-effect-source.json"
            if sha(effect) != "4853c97a724ac0b76847e107e4396912248320bdb029215bb2daa83fc74b1b03":
                raise ValueError("Ultra observed death-effect dependency changed")
            validate_staged_chunks(json.loads(effect.read_text(encoding="utf-8")), receipt)
            defaults = HERE / "profile-assets/ultra-default-spotskill-source.json"
            if sha(defaults) != "79a1486f090e0efeb8ddfa83af0deeed34fdbb05e8fe672c60f32b9682b0b898":
                raise ValueError("Ultra observed default skill sources changed")
            validate_staged_chunks(json.loads(defaults.read_text(encoding="utf-8")), receipt)
        elif profile["productId"] == "special-chatterbox":
            closure = HERE / "profile-assets/chatterbox-monster-mechanical-resource-closure.json"
            if sha(closure) != "a0c27830795578fdac3bcdb37a4c79d5542f92117543f4ad54c93d941c356b4c":
                raise ValueError("Chatterbox original monster resource source changed")
            validate_staged_chunks(json.loads(closure.read_text(encoding="utf-8")), receipt)
            effect = HERE / "profile-assets/chatterbox-red-death-effect-source.json"
            if sha(effect) != "1af639b66efd3da99b18c711b3f8592c82fa64823fdd83cbf5c03ce535705ac3":
                raise ValueError("Chatterbox observed death-effect dependency changed")
            validate_staged_chunks(json.loads(effect.read_text(encoding="utf-8")), receipt)
            defaults = HERE / "profile-assets/chatterbox-default-spotskill-source.json"
            if sha(defaults) != "72bc1138a298cf00dc03f8b6a4c79941204075646da8dce332cf2c00707249c3":
                raise ValueError("Chatterbox observed default skill sources changed")
            validate_staged_chunks(json.loads(defaults.read_text(encoding="utf-8")), receipt)
    return path
