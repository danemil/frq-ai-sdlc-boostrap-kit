"""The commands behind setup.py. Each returns (exit code, lines to print).

The lines are short and plain: Copilot relays them to the person as they are.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import checks, conflicts, exclude, packs, paths, place, reuse, state
from .connectors import manage, registry
from .paths import SetupError  # noqa: F401  setup.py catches commands.SetupError


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


def _skill_id(value) -> str:
    """A skill id as the kit's library names it: `ai-sdlc-drawio` and `drawio` are the same."""
    value = (value or "").strip()
    return value[len(packs.PREFIX):] if value.startswith(packs.PREFIX) else value


def _skill(kit, value, verb="added") -> str:
    value = _skill_id(value)
    if value in packs.UNSUPPORTED_SKILLS:
        raise SetupError(f"The skill {value} cannot be {verb}: {packs.UNSUPPORTED_SKILLS[value]}.")
    if value not in packs.available_skills(kit):
        raise SetupError(f"There is no skill {value}. Available: "
                         f"{', '.join(packs.available_skills(kit))}.")
    return value


def _clean_skill_choices(kit, c, forget_added=True) -> list[str]:
    """Repair skill names an older kit stored unchecked: `ai-sdlc-x` becomes `x`, and a skill
    the kit does not have is forgotten (left-out ones always; added ones when forget_added,
    update reports those itself). Returns a summary line for each repair."""
    known, lines = set(packs.available_skills(kit)), []
    for key in ("add_skills", "drop_skills"):
        kept = []
        for s in c[key]:
            sid = _skill_id(s)
            if sid in known:
                if sid != s:
                    lines.append(f"- Your choices named the skill {s}; it is {sid} now.")
                kept.append(sid)
            elif key == "drop_skills" or forget_added:
                what = "left out" if key == "drop_skills" else "added"
                lines.append(f"- Your choices {what} a skill the kit does not have ({s}); "
                             "that entry is gone.")
            else:
                kept.append(s)
        c[key] = sorted(set(kept))
    return lines


def _need_state(root) -> dict:
    st = state.load(root)
    if st is None:
        raise SetupError('The kit is not set up in this repo yet. Say "do the onboarding".')
    return st


def _need_whole_kit(kit, copied: bool, command: str) -> None:
    """Refuse a kit folder that cannot set anyone up, before anything moves (place.validate_kit)."""
    problems = place.validate_kit(kit)
    if not problems:
        return
    shown = ", ".join(problems[:3]) + (", …" if len(problems) > 3 else "")
    if copied:
        raise SetupError(f"This kit copy is incomplete ({shown}). Copy the whole kit folder "
                         "again (without .git) and retry. Nothing was changed.")
    raise SetupError(f"The kit folder {paths.KIT_REL} is incomplete ({shown}). Copy the whole "
                     "kit folder into the repo again (without .git) and run "
                     f"python3 <that folder>/setup.py {command}. Nothing was changed.")


# --- summaries -----------------------------------------------------------------

def _where(rels, verbose=False) -> str:
    """The files as a list (verbose), or as counts per folder: a skill's files count under
    .agents/skills/ with the number of skills, any other file under its own folder."""
    if verbose:
        return ", ".join(rels)
    groups, skills = {}, {}
    for rel in rels:
        parts = rel.split("/")
        if rel.startswith(".agents/skills/") and len(parts) > 3:
            folder = ".agents/skills/"
            skills.setdefault(folder, set()).add(parts[2])
        else:
            folder = rel.rsplit("/", 1)[0] + "/" if "/" in rel else "./"
        groups[folder] = groups.get(folder, 0) + 1
    out = []
    for folder, n in sorted(groups.items()):
        k = len(skills.get(folder, ()))
        out.append(f"{folder} ({n} in {k} skill{'s' if k != 1 else ''})" if k else f"{folder} ({n})")
    return ", ".join(out)


def _summary(verb, root, is_git, kit, all_packs, st, report, verbose=False) -> list[str]:
    c = st["choices"]
    combined = packs.combine(all_packs, c)
    roles = ", ".join(all_packs[r]["label"] for r in c["roles"])
    lines = [f"{verb} AI-SDLC {paths.kit_version(kit)} for {c['name']}: {roles} · "
             f"{packs.LANGUAGES[c['lang']]}."]
    lines.append("- Hidden from git: .ai-sdlc/ and every ai-sdlc-* file." if is_git else
                 "- This folder is not a git repo, so nothing hides these files from git.")
    if report["written"]:
        lines.append(f"- Wrote {len(report['written'])} file(s): "
                     f"{_where(report['written'], verbose)}")
    if report["removed"]:
        lines.append(f"- Removed {len(report['removed'])} file(s) no longer needed: "
                     f"{_where(report['removed'], verbose)}")
    for rel in report["kept"]:
        if rel + place.SIDECAR in report["written"]:
            lines.append(f"- Kept your edit in {rel}. The kit's newer copy is next to it as "
                         f"{rel}{place.SIDECAR}, for you to compare.")
        elif rel in st["files"]:
            lines.append(f"- Kept your edit in {rel}. The kit's copy has not changed, so there "
                         "is nothing to compare.")
        else:
            lines.append(f"- Kept your edit in {rel}. Your choices no longer need it; delete it "
                         "if you don't need it either.")
    for item in report["skipped"]:
        lines.append(f"- Left alone: {item}")
    skills = ", ".join(packs.PREFIX + s for s in combined["skills"]) or "none"
    lines.append(f"- Skills: {skills} · git: {combined['git_comfort']} · session summary: "
                 f"{'on' if combined['rituals'] == 'status' else 'off'}")
    return lines + _connectors_line(all_packs, c["roles"], st.get("skipped_connectors", []))


def _connectors_line(all_packs, roles, skipped=()) -> list[str]:
    """One line: the connectors the roles usually need, each marked when already connected
    or skipped (connect --suggested); a skipped one is not suggested again.
    Names only, never a value; a connector problem never stops a setup summary."""
    names = packs.role_connectors(all_packs, roles)
    if not names:
        return []
    try:
        found = registry.discover()
    except Exception:  # noqa: BLE001  a broken module must not break setup
        found = {}
    shown, todo = [], []
    for name in names:
        c = found.get(name)
        connected = bool(c) and manage.is_connected(c)
        if connected:
            shown.append(f"{name} (connected)")
        elif name in skipped:
            shown.append(f"{name} (skipped)")
        else:
            shown.append(name)
            todo.append(name)
    hint = f" (say 'connect {todo[0]}')" if todo else ""
    return [f"- Connectors for your roles: {', '.join(shown)}{hint}"]


# --- commands -------------------------------------------------------------------

def cmd_setup(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    kit = Path(kit).resolve()
    if not place.is_kit(kit):
        raise SetupError(f"{kit} is not a complete kit folder (setup.py, VERSION, roles/).")
    dest = root / paths.KIT_REL
    _need_whole_kit(kit, kit != dest, "setup")      # before anything changes
    if is_git:
        exclude.protect(root)                       # first: hide the destination
    try:
        if (kit != dest and root in kit.parents and state.load(root) is None
                and place.is_kit(dest)):
            kit = place.replace_kit(root, kit)      # an unfinished setup's kit folder: replace it
        else:
            kit = place.move_kit(root, kit)         # second: move the copied kit there
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
    lines = _summary("Set up", root, is_git, kit, all_packs, st, report, args.verbose)
    lines.append('Say "change my preferences", "update the kit" or "remove the kit" at any time.')
    return 0, lines + _check_lines(root)[1]


def _check_lines(root) -> tuple[int, list[str]]:
    """Exit 0 for nothing or notices only, 1 when there is a problem (checks.is_notice)."""
    st, found = checks.run(root)
    if not found:
        return 0, ["Check: all good."]
    items = [f"- [{fid}] {text}" for fid, text in found]
    if all(checks.is_notice(fid) for fid, _ in found):
        return 0, [f"Check: nothing to fix; {len(found)} notice(s) to read:"] + items
    return 1, [f"Check: {len(found)} to look at:"] + items


def cmd_check(args, cwd, kit):
    if args.quiet:
        try:
            root, _ = paths.repo_root(cwd)
            st, found = checks.run(root)
            return 0, [checks.quiet_line(root, st, found)]
        except Exception as exc:  # noqa: BLE001  the session-start check must never fail
            return 0, [f"AI-SDLC: the check could not run ({exc})."]
    root, _ = paths.repo_root(cwd)
    code, lines = _check_lines(root)
    st = state.load(root)
    if st is not None:            # name the role connectors, so nobody has to guess them
        try:
            all_packs = packs.load(root / paths.KIT_REL)
            roles = [r for r in st["choices"]["roles"] if r in all_packs]
            lines += _connectors_line(all_packs, roles, st.get("skipped_connectors", []))
        except Exception:  # noqa: BLE001  a broken kit folder is reported above; never fail here
            pass
    return code, lines


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
    adds = [_skill(kit, s) for s in args.add_skill]            # every name checked first
    drops = [_skill(kit, s, "left out") for s in args.drop_skill]
    repaired = _clean_skill_choices(kit, c)
    for s in adds:
        c["add_skills"] = sorted(set(c["add_skills"]) | {s})
        c["drop_skills"] = [x for x in c["drop_skills"] if x != s]
    for s in drops:
        c["drop_skills"] = sorted(set(c["drop_skills"]) | {s})
        c["add_skills"] = [x for x in c["add_skills"] if x != s]
    if is_git:
        exclude.protect(root)
    report = place.apply(root, st, place.wanted_files(kit, all_packs, c))
    state.save(root, st)
    return 0, (_summary("Updated", root, is_git, kit, all_packs, st, report, args.verbose)
               + repaired
               + _check_lines(root)[1])


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
    _need_whole_kit(kit, kit != dest, "update")   # before anything changes
    all_packs = packs.load(kit)
    c = st["choices"]
    gone = [r for r in c["roles"] if r not in packs.selectable(all_packs)]
    c["roles"] = [r for r in c["roles"] if r not in gone]
    repaired = _clean_skill_choices(kit, c, forget_added=False)
    lost = [s for s in c["add_skills"] if s not in packs.available_skills(kit)]
    c["add_skills"] = [s for s in c["add_skills"] if s not in lost]
    wanted = place.wanted_files(kit, all_packs, c)  # prepared from the copy, before it moves
    if is_git:
        exclude.protect(root)                     # the newer kit may hide more paths
    moved = None
    if kit != dest:
        old_version = paths.kit_version(dest) if place.is_kit(dest) else None
        try:
            place.replace_kit(root, kit)
        except FileExistsError:
            raise SetupError(f"{paths.KIT_REL} is not a kit folder; it was left alone.") from None
        moved = (f"- Moved {kit.relative_to(root).as_posix()} into {paths.KIT_REL}"
                 + (f" (replaced {old_version})." if old_version else "."))
    report = place.apply(root, st, wanted)
    known = set(registry.names())                 # a skip for a connector the kit lost goes
    st["skipped_connectors"] = [n for n in st["skipped_connectors"] if n in known]
    st["kit_version"] = paths.kit_version(dest)
    state.save(root, st)
    lines = _summary("Updated to", root, is_git, dest, all_packs, st, report, args.verbose)
    if moved:
        lines.insert(1, moved)
    if gone:
        lines.append(f"- The newer kit has no {', '.join(gone)} role any more; it was dropped.")
    if lost:
        lines.append(f"- The newer kit has no {', '.join(lost)} skill any more; it was dropped.")
    return 0, lines + repaired + _check_lines(root)[1]


def _remove_plan(root, st) -> tuple[int, list[str]]:
    """(files remove would delete, files it would keep because they were edited): a dry run."""
    tracked = paths.tracked(root, set(st["files"]))
    gone, kept = 0, []
    for rel in sorted(st["files"]):
        if rel in tracked:
            continue
        fs = reuse.file_state(root, st, rel)
        if fs == reuse.CLEAN:
            gone += 1
        elif fs == reuse.MODIFIED:
            kept.append(rel)
    return gone, kept


def cmd_remove(args, cwd, kit):
    root, is_git = paths.repo_root(cwd)
    st = _need_state(root)
    personal = [r for r in checks.ai_sdlc_files(root) if paths.is_personal(r)]
    if not args.yes:                              # say what would happen; change nothing
        gone, kept = _remove_plan(root, st)
        lines = [f"Nothing was removed yet. remove takes out {gone} kit file(s) you never "
                 f"edited, the kit folder {paths.KIT_REL} and your settings."]
        if kept:
            lines.append("Kept, because you edited them: " + ", ".join(kept))
        if personal:
            lines.append("Kept, your personal notes and skills: " + ", ".join(personal))
        lines.append("Your connector logins stay.")
        lines.append("Remove the kit from this repo? Only after a yes: "
                     "python3 .ai-sdlc/kit/setup.py remove --yes")
        return 2, lines
    report = place.apply(root, st, {})            # deletes unedited files, keeps edited ones
    kit_dir = root / paths.KIT_REL
    if place.is_kit(kit_dir):
        shutil.rmtree(kit_dir)
    (root / paths.STATE_REL).unlink()
    home = root / paths.HOME_REL
    if home.is_dir() and not any(home.iterdir()):
        home.rmdir()
    if is_git and personal:
        exclude.protect(root, exclude.PERSONAL_PATTERNS)   # keep only the person's own files hidden
    elif is_git:
        exclude.unprotect(root)
    lines = [f"Removed the kit: {len(report['removed'])} file(s), the kit folder and your settings."]
    if report["kept"]:
        lines.append("Kept, because you edited them (git now shows them; delete them if you "
                     "don't need them): " + ", ".join(report["kept"]))
    if personal:
        lines.append(("Kept your personal notes and skills, still hidden from git: " if is_git
                      else "Kept your personal notes and skills: ") + ", ".join(personal)
                     + (". Delete them if you don't need them." if not is_git else
                        ". If you set the kit up again it uses them; delete them if you don't "
                        "need them."))
    if is_git and not report["kept"] and not personal:
        lines.append("The repo is back to how it was before setup.")
    return 0, lines


def _state_or_none(cwd):
    """(root, state) for the repo at cwd; state is None when it is not set up or unreadable."""
    try:
        root, _ = paths.repo_root(cwd)
    except SetupError:            # connectors work in any folder, even one git refuses
        return Path(cwd), None
    try:
        return root, state.load(root)
    except Exception:  # noqa: BLE001  connectors work in any folder, set up or not
        return root, None


def cmd_connect(args, cwd, kit):
    if bool(args.name) == bool(args.suggested) or (args.suggested and args.test):
        raise SetupError("Use either connect <connector> or connect --suggested "
                         "(--test goes with a connector name).")
    if args.suggested:
        return _connect_suggested(cwd)
    code, lines = manage.connect(args.name, test_only=args.test)
    root, st = _state_or_none(cwd)
    if not args.test and code in (0, 1) and st and args.name in st["skipped_connectors"]:
        st["skipped_connectors"].remove(args.name)  # saved now, so no longer skipped
        state.save(root, st)
    return code, lines


def _connect_suggested(cwd):
    root, _ = paths.repo_root(cwd)
    st = _need_state(root)
    all_packs = packs.load(root / paths.KIT_REL)
    defaults = packs.role_connectors(all_packs, [r for r in st["choices"]["roles"]
                                                 if r in all_packs])
    code, lines, result = manage.suggest(defaults)
    skipped = sorted((set(st["skipped_connectors"]) | set(result["skipped"]))
                     - set(result["connected"]))
    if skipped != st["skipped_connectors"]:
        st["skipped_connectors"] = skipped
        state.save(root, st)
    return code, lines


def cmd_connections(args, cwd, kit):
    _, st = _state_or_none(cwd)
    return manage.connections(skipped=st["skipped_connectors"] if st else ())


def cmd_disconnect(args, cwd, kit):
    return manage.disconnect(args.name, yes=args.yes)


HANDLERS = {
    "setup": cmd_setup,
    "change": cmd_change,
    "update": cmd_update,
    "check": cmd_check,
    "ack": cmd_ack,
    "remove": cmd_remove,
    "connect": cmd_connect,
    "connections": cmd_connections,
    "disconnect": cmd_disconnect,
}


def run(args, cwd, kit):
    return HANDLERS[args.command](args, cwd, kit)
