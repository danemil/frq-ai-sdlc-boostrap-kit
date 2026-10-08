"""The six commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import checks, conflicts, exclude, packs, paths, place, state


class SetupError(Exception):
    """A plain-language reason to stop. Raised before anything else is changed."""


# --- argument checks ---------------------------------------------------------

def _name(value) -> str:
    name = " ".join((value or "").split())
    if not name or len(name) > 80:
        raise SetupError("Please give a name (1 to 80 characters).")
    return name


def _roles(all_packs, value) -> list[str]:
    roles = [r.strip().lower() for r in (value or "").split(",") if r.strip()]
    known = packs.selectable(all_packs)
    unknown = [r for r in roles if r not in known]
    if not roles or unknown:
        raise SetupError(f"Choose one or more roles from: {', '.join(known)}"
                         + (f" (not known: {', '.join(unknown)})." if unknown else "."))
    return list(dict.fromkeys(roles))


def _lang(value) -> str:
    if value not in packs.LANGUAGES:
        raise SetupError(f"Choose a language from: {', '.join(packs.LANGUAGES)}.")
    return value


def _skill(kit, value) -> str:
    if value in packs.UNSUPPORTED_SKILLS:
        raise SetupError(f"The skill {value} cannot be added: {packs.UNSUPPORTED_SKILLS[value]}.")
    if value not in packs.available_skills(kit):
        raise SetupError(f"There is no skill {value}. Available: "
                         f"{', '.join(packs.available_skills(kit))}.")
    return value


def _need_state(root) -> dict:
    st = state.load(root)
    if st is None:
        raise SetupError('The kit is not set up in this repo yet. Say "do the onboarding".')
    return st


# --- summaries -----------------------------------------------------------------

def _summary(verb, root, is_git, kit, all_packs, st, report) -> list[str]:
    c = st["choices"]
    combined = packs.combine(all_packs, c)
    roles = ", ".join(all_packs[r]["label"] for r in c["roles"])
    lines = [f"{verb} AI-SDLC {paths.kit_version(kit)} for {c['name']}: {roles} · "
             f"{packs.LANGUAGES[c['lang']]}."]
    lines.append("- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file." if is_git else
                 "- This folder is not a git repo, so nothing hides these files from git.")
    if report["written"]:
        lines.append(f"- Wrote {len(report['written'])} file(s): {', '.join(report['written'])}")
    if report["removed"]:
        lines.append(f"- Removed {len(report['removed'])} file(s) no longer needed: "
                     f"{', '.join(report['removed'])}")
    for rel in report["kept"]:
        lines.append(f"- Kept your edit in {rel}. The kit's copy, if it changed, is next to it "
                     f"as {rel}{place.SIDECAR}.")
    for item in report["skipped"]:
        lines.append(f"- Left alone: {item}")
    skills = ", ".join(packs.PREFIX + s for s in combined["skills"]) or "none"
    lines.append(f"- Skills: {skills} · git: {combined['git_comfort']} · session summary: "
                 f"{'on' if combined['rituals'] == 'status' else 'off'}")
    return lines


# --- commands -------------------------------------------------------------------

def cmd_setup(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    kit = Path(kit).resolve()
    if not place.is_kit(kit):
        raise SetupError(f"{kit} is not a complete kit folder (setup.py, VERSION, roles/).")
    if is_git:
        exclude.protect(root)                       # first: hide the destination
    try:
        kit = place.move_kit(root, kit)             # second: move the copied kit there
    except ValueError:
        raise SetupError(f"Copy the kit folder into the repo first; it is at {kit}, "
                         f"outside {root}.") from None
    except FileExistsError:
        raise SetupError('A kit is already set up in this repo (.ai-sdlc/kit). To use this '
                         'newer copy, say "update the kit".') from None
    if args.protect_only:
        return 0, ["The kit is now in .ai-sdlc/kit" + (" and hidden from git." if is_git else
                   ". This folder is not a git repo, so nothing hides it from git."),
                   "Next: python3 .ai-sdlc/kit/setup.py setup --name … --roles … --lang …"]
    all_packs = packs.load(kit)
    choices = {"name": _name(args.name), "roles": _roles(all_packs, args.roles),
               "lang": _lang(args.lang)}
    st = state.load(root) or state.new(paths.kit_version(kit))
    st["choices"].update(choices)
    report = place.apply(root, st, place.wanted_files(kit, all_packs, st["choices"]))
    st["kit_version"] = paths.kit_version(kit)
    state.save(root, st)                            # last
    lines = _summary("Set up", root, is_git, kit, all_packs, st, report)
    lines.append('Say "change my preferences", "update the kit" or "remove the kit" at any time.')
    return 0, lines + _check_lines(root)[1]


def _check_lines(root) -> tuple[int, list[str]]:
    st, found = checks.run(root)
    if not found:
        return 0, ["Check: all good."]
    return 1, [f"Check: {len(found)} to look at:"] + [f"- [{fid}] {text}" for fid, text in found]


def cmd_check(args, cwd, kit):
    root, _ = paths.repo_root(cwd)
    if args.quiet:
        try:
            st, found = checks.run(root)
            return 0, [checks.quiet_line(root, st, found)]
        except Exception as exc:  # noqa: BLE001  the session-start check must never fail
            return 0, [f"AI-SDLC: the check could not run ({exc})."]
    return _check_lines(root)


def cmd_ack(args, cwd, kit):
    root, _ = paths.repo_root(cwd)
    st = _need_state(root)
    current = {wid: fp for wid, _, fp in conflicts.warnings(root, st)}
    unknown = [wid for wid in args.ids if wid not in current]
    if unknown:
        raise SetupError(f"No current warning has the id {', '.join(unknown)}. "
                         "Run check to see the ids.")
    for wid in args.ids:
        st["acks"][wid] = current[wid]
    state.save(root, st)
    return 0, [f"Noted {wid}. It comes back only if that team file changes." for wid in args.ids]


def cmd_change(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    kit = root / paths.KIT_REL
    all_packs = packs.load(kit)
    c = st["choices"]
    if args.name is not None:
        c["name"] = _name(args.name)
    if args.roles is not None:
        c["roles"] = _roles(all_packs, args.roles)
    if args.lang is not None:
        c["lang"] = _lang(args.lang)
    if args.git_comfort is not None:
        c["git_comfort"] = None if args.git_comfort == "default" else args.git_comfort
    if args.rituals is not None:
        c["rituals"] = None if args.rituals == "default" else args.rituals
    for s in args.add_skill:
        _skill(kit, s)
        c["add_skills"] = sorted(set(c["add_skills"]) | {s})
        c["drop_skills"] = [x for x in c["drop_skills"] if x != s]
    for s in args.drop_skill:
        c["drop_skills"] = sorted(set(c["drop_skills"]) | {s})
        c["add_skills"] = [x for x in c["add_skills"] if x != s]
    if is_git:
        exclude.protect(root)
    report = place.apply(root, st, place.wanted_files(kit, all_packs, c))
    state.save(root, st)
    return 0, _summary("Updated", root, is_git, kit, all_packs, st, report) + _check_lines(root)[1]


def cmd_update(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    kit = Path(kit).resolve()
    dest = root / paths.KIT_REL
    if kit != dest:
        new, old = paths.kit_version(kit), paths.kit_version(dest)
        if checks.version_key(new) < checks.version_key(old):
            raise SetupError(f"This copy is older ({new}) than the kit set up here ({old}). "
                             "Nothing was changed.")
        if root not in kit.parents:
            raise SetupError(f"Copy the newer kit folder into the repo first; it is at {kit}.")
    if is_git:
        exclude.protect(root)                     # the newer kit may hide more paths
    if kit != dest:
        try:
            place.replace_kit(root, kit)
        except FileExistsError:
            raise SetupError(f"{paths.KIT_REL} is not a kit folder; it was left alone.") from None
    all_packs = packs.load(dest)
    c = st["choices"]
    gone = [r for r in c["roles"] if r not in packs.selectable(all_packs)]
    c["roles"] = [r for r in c["roles"] if r not in gone]
    report = place.apply(root, st, place.wanted_files(dest, all_packs, c))
    st["kit_version"] = paths.kit_version(dest)
    state.save(root, st)
    lines = _summary("Updated to", root, is_git, dest, all_packs, st, report)
    if gone:
        lines.append(f"- The newer kit has no {', '.join(gone)} role any more; it was dropped.")
    return 0, lines + _check_lines(root)[1]


def cmd_remove(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    personal = [r for r in checks.ai_sdlc_files(root) if paths.is_personal(r)]
    report = place.apply(root, st, {})            # deletes unedited files, keeps edited ones
    kit_dir = root / paths.KIT_REL
    if place.is_kit(kit_dir):
        shutil.rmtree(kit_dir)
    (root / paths.STATE_REL).unlink()
    home = root / paths.HOME_REL
    if home.is_dir() and not any(home.iterdir()):
        home.rmdir()
    if is_git:
        exclude.unprotect(root)
    lines = [f"Removed the kit: {len(report['removed'])} file(s), the kit folder and your settings."]
    if report["kept"]:
        lines.append("Kept, because you edited them (git now shows them; delete them if you "
                     "don't need them): " + ", ".join(report["kept"]))
    if personal:
        lines.append("Kept your personal notes and skills (git now shows them; delete them if "
                     "you don't need them): " + ", ".join(personal))
    if is_git and not report["kept"] and not personal:
        lines.append("The repo is back to how it was before setup.")
    return 0, lines


HANDLERS = {
    "setup": cmd_setup,
    "change": cmd_change,
    "update": cmd_update,
    "check": cmd_check,
    "ack": cmd_ack,
    "remove": cmd_remove,
}


def run(args, cwd, kit):
    return HANDLERS[args.command](args, cwd, kit)
