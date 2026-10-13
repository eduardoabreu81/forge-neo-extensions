# Builds a Forge Neo extension index from the A1111 index:
# - validates every repo via `gh api` (dead repos are dropped)
# - flags GitHub-archived repos with an "archived" tag
# - adds the curated Forge Neo ecosystem extensions tagged "forge-neo"
# Usage: python build_index_neo.py   (needs gh CLI logged in; caches validation in *.tsv)
import json
import re
import subprocess
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
BASE_INDEX = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
TODAY = "2026-10-13"

# existing index entries that run on Forge Neo (verified in discussion #1128)
NEO_COMPATIBLE_EXISTING = {
    "cheald/sd-webui-loractl",
    "hako-mikan/sd-webui-lora-block-weight",
    "hako-mikan/sd-webui-negpip",
    "hako-mikan/sd-webui-regional-prompter",
    "muerrilla/sd-webui-detail-daemon",
    "gutris1/sd-hub",
    "SignalFlagZ/sd-webui-civbrowser",
    "Haoming02/sd-webui-prompt-format",
    "Haoming02/sd-webui-vectorscope-cc",
    "Amadeus-AI/img2img-hires-fix",
    "bluelovers/sd-webui-pnginfo-beautify",
    "Extraltodeus/test_my_prompt",
    "hako-mikan/sd-webui-supermerger",
}

# repo -> (display name, category tags) — description comes from GitHub when usable
NEO_ADDITIONS = {
    "eduardoabreu81/iris-3b-forge-neo": ("Iris-3B for Forge Neo", ["models"]),
    "eduardoabreu81/minimax-h3-forge-neo": ("MiniMax H3 for Forge Neo", ["models"]),
    "eduardoabreu81/qwen2.1-forge-neo": ("Qwen-Image 2.1 for Forge Neo", ["models"]),
    "Haoming02/ADetailer-Neo": ("ADetailer-Neo", ["editing"]),
    "abzaloff/aadetailer-neoforge": ("ADetailer NeoForge", ["editing"]),
    "xXIlRizzoXx/adetailer-ultimate": ("ADetailer Ultimate", ["editing"]),
    "Anzhc/aadetailer-reforge": ("ADetailer Reforge", ["editing"]),
    "abzaloff/forge-neo-lama-cleaner": ("Lama Cleaner Neo", ["editing"]),
    "kainatquaderee/sd-webui-reactor-Nsfw_freedom": ("ReActor NSFW Freedom", ["editing"]),
    "ototadana/sd-face-editor": ("Face Editor", ["editing"]),
    "eduardoabreu81/sd-webui-prompt-all-in-one-neo": ("Prompt All In One NEO", ["prompting", "tab"]),
    "eduardoabreu81/sd-webui-tagcomplete-neo": ("TagComplete Neo", ["prompting"]),
    "eduardoabreu81/sd-webui-prompt-studio-neo": ("Prompt Studio Neo", ["prompting"]),
    "abzaloff/sd-dynamic-prompts": ("Dynamic Prompts Neo", ["prompting"]),
    "zeydsama/sd-forge-prompt-save": ("Prompt Save (Forge)", ["prompting"]),
    "Haoming02/sd-webui-yapping": ("Yapping", ["prompting"]),
    "eduardoabreu81/sd-wildcard-composer-neo": ("Wildcard Composer Neo", ["prompting"]),
    "abzaloff/composer_forge_neo": ("Composer Forge Neo", ["prompting"]),
    "abzaloff/sd-webui-lora-quickpick": ("LoRA Quickpick", ["script"]),
    "kiygskr/sd-webui-lora-block-weight-forgeneo-anima": ("LoRA Block Weight (ForgeNeo Anima)", ["script"]),
    "hako-mikan/sd-webui-traintrain": ("TrainTrain", ["training"]),
    "eduardoabreu81/sd-webui-merge-studio": ("Merge Studio", ["tab", "script"]),
    "kiygskr/sd-webui-supermerger-forgeneo-anima": ("SuperMerger (ForgeNeo Anima)", ["script", "tab"]),
    "aiai-r/sd-webui-supermerger-forgeneo-anima": ("SuperMerger ForgeNeo Anima (aiai-r)", ["script", "tab"]),
    "darkninjavn/sd-webui-runtime-merger-neo-Anima": ("Runtime Merger Neo Anima", ["script", "tab"]),
    "eduardoabreu81/sd-civitai-browser-neo": ("Civitai Browser Neo", ["tab", "models", "online"]),
    "masterofobzene/sd-civitai-browser-plus-NEO": ("Civitai Browser Plus NEO", ["tab", "models", "online"]),
    "Squibeel/models-info": ("Models Info (Neo)", ["models"]),
    "Metachs/sdwebui-nai-api": ("NAI API", ["models", "online"]),
    "cataclisma/sd-webui-agent-scheduler-neo": ("Agent Scheduler Neo", ["tab"]),
    "seti9585/sd-webui-tde-sampler": ("TDE Sampler", ["script"]),
    "seti9585/sd-webui-rk-sampler": ("RK Sampler", ["script"]),
    "zeydsama/sd-forge-res4lyf": ("RES4LYF (Forge)", ["script"]),
    "zeydsama/sd-forge-beta57": ("Beta57", ["script"]),
    "zeydsama/sd-forge-dlss5": ("DLSS5", ["script"]),
    "aoleg/Neo_ExtraSchedulers": ("Extra Schedulers (Neo)", ["script"]),
    "Haoming02/sd-forge-couple": ("Attention Couple", ["prompting"]),
    "Haoming02/sd-forge-ic-light": ("IC-Light", ["editing"]),
    "aoleg/neo-krea2-negpip": ("NegPiP (Krea 2)", ["prompting"]),
    "aoleg/neo-krea2-conditioning": ("Krea 2 Conditioning Control", ["prompting"]),
    "aoleg/Neo-Krea2-NAG": ("Krea2 NAG", ["prompting"]),
    "aoleg/ComfyUI-SPEED": ("SPEED", ["script"]),
    "aoleg/ComfyUI-Colorcraft": ("Colorcraft", ["editing", "manipulations"]),
    "aoleg/seedvr2-webui-neo-extension": ("SeedVR2 (Neo)", ["manipulations"]),
    "eduardoabreu81/sd-webui-state-manager-neo": ("State Manager Neo", ["UI related", "script"]),
    "BulbulLeung/forge-split-extra-networks": ("Split Extra Networks", ["UI related"]),
    "BulbulLeung/sd-generation-layout": ("Generation Layout", ["UI related"]),
    "diamfang/sd-webui-folder-switcher": ("Folder Switcher", ["UI related"]),
    "diamfang/sd-webui-smooth-progress": ("Smooth Progress", ["UI related"]),
    "masterofobzene/preset-manager-neo": ("Preset Manager Neo", ["script", "UI related"]),
    "seti9585/sd-webui-TIPO-PNGInfo-Restore": ("TIPO PNGInfo Restore", ["script"]),
    "hirorohi03/repeat-generate-4NEO": ("Repeat Generate 4NEO", ["script"]),
    "hirorohi03/stable-diffusion-webui-wd14-tagger": ("WD 1.4 Tagger (Neo)", ["script", "query"]),
    "sdprompts/xCloneCleaner": ("xCloneCleaner", ["models"]),
}


def gh_repo(repo):
    """repo -> (full_name, archived, pushed, stars, created, branch, description) or None if 404."""
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}", "--jq",
         '[.full_name, (.archived|tostring), (.pushed_at[:10]), (.stargazers_count|tostring), (.created_at[:10]), .default_branch, (.description // "")] | @tsv'],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return out.stdout.rstrip("\n").split("\t")  # rstrip only newline: empty description keeps the trailing tab


def load_cache(path):
    cache = {}
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 7:
                cache[parts[0]] = parts
    return cache


def main():
    base = json.loads((HERE / "a1111_index.json").read_text(encoding="utf-8"))
    tags_root = base.get("tags", {})
    tags_root["forge-neo"] = "Made for / verified with Forge Neo (sd-webui-forge-classic)"

    cache = load_cache(HERE / "idx_status.tsv")
    additions_cache = load_cache(HERE / "neo_status.tsv")

    extensions = []
    dropped, archived, neo_tagged = [], 0, 0

    for ext in base["extensions"]:
        url = ext.get("url", "")
        m = re.search(r"github\.com/([^/\" ]+)", url)
        repo = (ext.get("full_name") or (m.group(1) if m else "")).strip()
        if not m and "github.com" not in url:
            extensions.append(ext)  # non-GitHub host (e.g. the Gitea one) — keep as is
            continue
        info = cache.get(repo) or ([None] + gh_repo(repo))
        if not info or info[1] in (None, "DEAD"):
            dropped.append(repo)
            continue
        if info[2] == "true":
            dropped.append(f"{repo} (archived)")
            continue
        full, arch, pushed, stars, created, branch, gh_desc = info[1:8]
        entry = dict(ext)
        entry["full_name"] = full
        entry["url"] = f"https://github.com/{full}"
        entry["github_description"] = gh_desc
        entry["stars"] = int(stars)
        entry["created_at"] = f"{created}T00:00:00Z"
        entry["commit_time"] = f"{pushed}T00:00:00Z"
        entry["default_branch"] = branch
        entry_tags = entry.get("tags", [])
        if repo in NEO_COMPATIBLE_EXISTING or full in NEO_COMPATIBLE_EXISTING:
            if "forge-neo" not in entry_tags:
                entry_tags.append("forge-neo")
            neo_tagged += 1
        entry["tags"] = entry_tags
        if "forge-neo" in entry_tags:
            entry["name"] = "\U0001F7E2 " + entry["name"]  # green dot marker, visible in the EXTENSION column
        extensions.append(entry)

    def norm_url(u):
        return re.sub(r"\.git$", "", u.strip().rstrip("/"))

    seen = {norm_url(e["url"]) for e in extensions}
    for repo, (name, cat_tags) in NEO_ADDITIONS.items():
        canonical = f"https://github.com/{repo}"
        if norm_url(canonical) in seen:
            continue  # already in the base index under a .git/renamed URL
        info = additions_cache.get(repo) or ([None] + gh_repo(repo))
        if not info or info[1] in (None, "DEAD"):
            dropped.append(repo)
            continue
        # the additions TSV stores .name in col 1 (no owner) — the key IS the canonical owner/repo
        _, arch, pushed, stars, created, branch, gh_desc = info[1:8]
        full = repo
        desc = gh_desc if len(gh_desc) >= 20 else name
        extensions.append({
            "name": f"\U0001F7E2 {name}",
            "url": canonical,
            "description": desc,
            "added": TODAY,
            "tags": ["forge-neo"] + cat_tags,
            "full_name": full,
            "github_description": gh_desc,
            "stars": int(stars),
            "created_at": f"{created}T00:00:00Z",
            "commit_time": f"{pushed}T00:00:00Z",
            "default_branch": branch,
        })
        seen.add(norm_url(canonical))
        neo_tagged += 1

    out = {"tags": tags_root, "extensions": extensions}
    dest = HERE / "index.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"entradas: {len(extensions)} (base {len(base['extensions'])} + {len(NEO_ADDITIONS)} novas)")
    print(f"removidas ({len(dropped)}): " + ", ".join(dropped))
    print(f"com tag forge-neo: {neo_tagged}")
    print(f"salvo em: {dest}")


if __name__ == "__main__":
    main()
