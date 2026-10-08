"""The six commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations

from pathlib import Path

from . import checks, exclude, packs, paths, place, state


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


def not_built(args, cwd, kit):
    return 3, [f"setup.py {args.command}: not built yet"]


HANDLERS = {
    "setup": cmd_setup,
    "check": cmd_check,
}


def run(args, cwd, kit):
    return HANDLERS.get(args.command, not_built)(args, cwd, kit)
