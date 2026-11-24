"""The always-pause list (plan section 7.1): one matcher per entry, in list order. A matcher takes a Ctx and
returns a short reason when the call is a one-way door, else None. The list can be added to, never removed from;
tests/test_fence.py pins the ids. Matching is deliberately conservative: a false ask costs one click, a miss
costs a one-way door."""
from __future__ import annotations

import re
from pathlib import Path

from .fence import SHELL_TOOLS, WRITE_TOOLS


def _r(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


_URL = _r(r"(?:git\+)?(?:https?|ssh|git)://([^/\s'\"]+)")
_READ_TOKENS = {"get", "list", "read", "search", "find", "fetch", "query", "describe", "show", "view", "inspect",
                "download", "count", "check", "validate", "whoami", "info", "status", "logs", "events", "history",
                "preview"}
_READ_ONLY_CMDS = {"cat", "ls", "dir", "echo", "grep", "rg", "head", "tail", "type", "get-content", "gc", "wc",
                   "select-string", "stat", "file", "less", "more", "pwd", "gp"}
_GIT_READ = _r(r"^git\s+(-C\s+\S+\s+)?(log|diff|status|show|branch\s*$|rev-parse|remote\s+-v|blame|ls-files)")


def _first(segment: str) -> str:
    word = segment.split(None, 1)[0] if segment.split() else ""
    return word.strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()


def _read_only(segment: str) -> bool:
    return _first(segment) in _READ_ONLY_CMDS or bool(_GIT_READ.match(segment))


def _mcp(ctx) -> bool:
    return ctx.tool.startswith("mcp__")


_CHANGE_VERBS = {"send", "post", "reply", "create", "update", "delete", "remove", "set", "add", "write", "upload",
                 "deploy", "publish", "manage", "generate", "rotate", "transfer", "restart", "destroy", "drop",
                 "purge", "erase", "trash", "log", "submit", "issue", "mint", "attach", "share", "forward",
                 "invite", "broadcast", "notify", "comment", "schedule", "terminate", "wipe", "clear", "sign",
                 "release", "regenerate", "revoke", "change"}


def _tool(ctx, verbs: set, nouns: set | None = None) -> bool:
    if not _mcp(ctx) or not (ctx.tokens & verbs):
        return False
    if ctx.tokens & _READ_TOKENS and not ctx.tokens & _CHANGE_VERBS:
        return False
    return nouns is None or bool(ctx.tokens & nouns)


def _hit(ctx, pattern: re.Pattern, per_segment: bool = False) -> bool:
    if per_segment:
        return any(pattern.search(s) for s in ctx.segments)
    return bool(pattern.search(ctx.cmd))


# --- the entries ------------------------------------------------------------------------------------------

_PROD = _r(r"(?<![A-Za-z0-9])(prod|production|prd)(?![A-Za-z0-9])")


def production(ctx):
    extra = [_r(p) for p in ctx.fence.get("production_markers") or []]
    pats = [_PROD, *extra]
    if ctx.tool in SHELL_TOOLS:
        live = [s for s in ctx.segments if not _read_only(s)]
        if any(p.search(s) for p in pats for s in live):
            return "the command names production; production anything is a one-way door"
    elif _mcp(ctx) or ctx.tool in ("WebFetch", "WebSearch"):
        if any(p.search(v) for p in pats for v in ctx.values()):
            return "the call names production; production anything is a one-way door"


_SEND_CMD = _r(r"\b(sendmail|msmtp|mutt|swaks)\b|\bmail\s+-s\b|\bgh\s+(pr|issue)\s+(comment|create|review|merge|close)"
               r"|\bgh\s+release\s+create\b|\bglab\s+(mr|issue)\s+(note|create|merge)\b")
_HTTP = _r(r"(^|\s)(curl|wget|http|https|xh|invoke-restmethod|irm|invoke-webrequest|iwr|postman\s+request)(\s|$)")
_HTTP_WRITE = _r(r"(-X\s*|--request\s+|-Method\s+|postman\s+request\s+)(POST|PUT|PATCH|DELETE)\b"
                 r"|\s(-d|--data\S*|--json|-F|--form|-Body)\s")


def outward(ctx):
    if ctx.tool in SHELL_TOOLS and (_hit(ctx, _SEND_CMD) or (_hit(ctx, _HTTP) and _hit(ctx, _HTTP_WRITE))):
        return "this sends something out of the machine to a person or a service"
    if _tool(ctx, {"send", "post", "reply", "publish", "broadcast", "notify", "comment", "invite", "share",
                   "schedule", "forward"}):
        return "this tool sends or posts to someone else"


_SIGN = _r(r"\bgpg\b.*--?(sign|detach-sign|clearsign|s\b)|\bcosign\s+sign\b|\bsigntool\b|\bgit\s+tag\s+.*-s\b")


_NUMBER = _r(r"(?:^|[\\/\s])gp(?:\.cmd)?\s+number\b")


def irreversible(ctx):
    if ctx.tool in SHELL_TOOLS and any(_NUMBER.search(seg) for seg in ctx.segments):
        return "an issued document number cannot be deleted"
    if ctx.tool in SHELL_TOOLS and _hit(ctx, _SIGN):
        return "a signature cannot be taken back"
    if _tool(ctx, {"log", "create", "add", "submit"}, {"time", "worklog", "timesheet", "spent"}):
        return "a time log entry is an irreversible record"
    if _tool(ctx, {"generate", "issue", "mint", "assign", "create"}, {"number", "invoice", "certificate", "receipt"}):
        return "an issued document number cannot be deleted"
    if _tool(ctx, {"sign", "esign"}) or "esign" in ctx.tokens:
        return "a signature cannot be taken back"


_APPROVED = _r(r"^\s*status:\s*approved\b")
_APPROVING = _r(r"status:\s*approved")


def _canonical(path: Path | None, project: Path) -> bool:
    return bool(path) and path.name.endswith(".canonical.yaml") and path.parent.name == "requirements" \
        and (project / "greenfield") in path.parents


_ACCEPT = _r(r"(?:^|[\\/\s])gp(?:\.cmd)?\s+(?:accept-line|pack\s+accept)\b")


def scope(ctx):
    path = ctx.path
    if _canonical(path, ctx.project):
        current = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        edits = ctx.inp.get("edits") or []
        new = " ".join([str(ctx.inp.get("content") or ""), str(ctx.inp.get("new_string") or ""),
                        *[str(e.get("new_string") or "") for e in edits if isinstance(e, dict)]])
        if any(_APPROVED.match(line) for line in current.splitlines()) or _APPROVING.search(new):
            return "the baseline is approved or is being approved; changing scope is the owner's"
    if ctx.tool in SHELL_TOOLS and any(_ACCEPT.search(seg) for seg in ctx.segments):
        return "accepting a line (or a pack hash) is the owner's decision, not the agent's"
    if ctx.tool in SHELL_TOOLS and ".canonical.yaml" in ctx.cmd and any(not _read_only(s) for s in ctx.segments):
        return "the canonical requirement is changed by a command; edit it with the editor tools so the diff shows"


_RM = {"rm", "rmdir", "del", "erase", "rd", "remove-item", "ri", "unlink", "shred", "truncate"}
_DELETE_CMD = _r(r"\bgit\s+(clean|reset\s+--hard|branch\s+-D|stash\s+(drop|clear)|checkout\s+--\s|restore\b(?!\s+--staged))"
                 r"|\bfind\b.*\s-delete\b|\brmtree\b|os\.(remove|unlink)\b|\.unlink\(|"
                 r"\b(drop\s+(table|database|schema)|truncate\s+table|delete\s+from)\b")


def delete_data(ctx):
    if ctx.tool in SHELL_TOOLS and (any(_first(s) in _RM for s in ctx.segments) or _hit(ctx, _DELETE_CMD)):
        return "this deletes data or evidence"
    if _tool(ctx, {"delete", "remove", "drop", "purge", "erase", "trash", "truncate", "wipe", "clear"}):
        return "this tool deletes data"


_UPLOAD = _r(r"(?:^|\s)(?:-d|--data\S*|--json|--upload-file|-T|-F|--form|-f|-Body)\s+\S*@")
_COPY_OUT = {"scp", "rsync", "sftp", "ftp", "rclone", "nc", "ncat", "netcat", "wormhole", "croc"}
_CLOUD_COPY = _r(r"^(aws\s+s3\s+(cp|sync|mv)|gsutil\s+(cp|rsync|mv)|az\s+storage\s+(blob|file)\s+upload"
                 r"|gh\s+gist\s+create|gh\s+release\s+upload)\b")


def sponsor_data(ctx):
    if ctx.tool in SHELL_TOOLS:
        if _hit(ctx, _HTTP) and _hit(ctx, _UPLOAD):
            return "a file leaves the machine; a human double-checks sponsor data first"
        if any(_first(s) in _COPY_OUT or _CLOUD_COPY.match(s) for s in ctx.segments):
            return "a file leaves the machine; a human double-checks sponsor data first"
    if _tool(ctx, {"upload", "attach", "attachment"}):
        return "this tool uploads a file; a human double-checks sponsor data first"


_PLATFORM_DELETE = _r(r"\bgh\s+repo\s+delete\b|\bglab\s+repo\s+delete\b|\bkubectl\s+delete\b|\bterraform\s+destroy\b"
                      r"|\bdocker\s+(rm|rmi|system\s+prune|volume\s+rm|network\s+rm)\b|\bdocker\s+compose\s+down\s+.*-v"
                      r"|\bheroku\s+apps:destroy\b|\bvercel\s+(remove|rm)\b|\bnetlify\s+sites:delete\b"
                      r"|\bfly(ctl)?\s+apps\s+destroy\b|\baws\s+.*\b(delete|terminate)-\S+|\bgcloud\s+.*\bdelete\b"
                      r"|\baz\s+.*\bdelete\b|\bhelm\s+uninstall\b|\bgit\s+push\s+.*(--delete|\s-d\s|\s:\S)")
_PLATFORM_NOUNS = {"project", "app", "repo", "repository", "service", "database", "bot", "workspace", "server",
                   "channel", "site", "cluster", "instance", "bucket", "namespace"}


def delete_platform(ctx):
    if ctx.tool in SHELL_TOOLS and _hit(ctx, _PLATFORM_DELETE):
        return "this deletes an app, repo or project on a platform"
    if _tool(ctx, {"delete", "remove", "destroy", "terminate"}, _PLATFORM_NOUNS):
        return "this deletes an app, repo or project on a platform"


_CRED_CMD = _r(r"\b(create|rotate|generate|issue|mint|regenerate|reset|revoke)[-_ ](api[-_ ]|access[-_ ]|auth[-_ ]"
               r"|upload[-_ ]|secret[-_ ])?(tokens?|keys?|secrets?|credentials?|passwords?)\b|\bssh-keygen\b"
               r"|\bopenssl\s+(genrsa|genpkey|rand|req\s+.*-newkey)\b|\bgh\s+auth\s+(login|token|refresh)\b"
               r"|\b(gcloud\s+auth|aws\s+configure|aws\s+sts|az\s+login)\b|\bvault\s+(write|kv\s+put|token\s+create)\b"
               r"|\bkubectl\s+create\s+secret\b|\bdocker\s+login\b")


def credentials(ctx):
    if ctx.tool in SHELL_TOOLS and _hit(ctx, _CRED_CMD):
        return "this creates or rotates a credential or token"
    if _tool(ctx, {"create", "rotate", "generate", "mint", "issue", "regenerate", "revoke", "manage", "set", "delete"},
             {"token", "tokens", "secret", "secrets", "credential", "credentials", "key", "keys", "password"}):
        return "this creates or rotates a credential or token"


_SHARED_ENV = _r(r"\bkubectl\s+(apply|patch|edit|scale|rollout|set|replace|annotate|label|cordon|drain)\b"
                 r"|\bhelm\s+(install|upgrade|rollback)\b|\bterraform\s+apply\b|\bpulumi\s+up\b|\bansible-playbook\b"
                 r"|\bargocd\s+app\s+(sync|set|rollback|delete)\b|\bsystemctl\s+(start|stop|restart|enable|disable)\b")


def shared_env(ctx):
    if ctx.tool in SHELL_TOOLS and _hit(ctx, _SHARED_ENV):
        return "this changes an environment other projects share"
    if _tool(ctx, {"set", "transfer", "change", "update"},
             {"access", "owner", "owners", "quota", "domain", "autoscaling", "permission", "permissions", "role",
              "acl", "firewall", "dns", "network"}) or "restart" in ctx.tokens and _mcp(ctx):
        return "this changes access or settings of a shared environment"


_RUNNERS = {"python", "python3", "py", "pytest", "node", "npm", "npx", "pnpm", "yarn", "bun", "go", "cargo", "dotnet",
            "java", "mvn", "gradle", "ruby", "bundle", "rake", "php", "bash", "sh", "make"}
_DEPLOY = _r(r"^(vercel|netlify|fly|flyctl|firebase|serverless|sls|sam|cdk|wrangler|heroku|railway|render|surge)\b"
             r".*\b(deploy|publish|release|push)\b|^docker\s+push\b|^(npm|yarn|pnpm)\s+publish\b|^twine\s+upload\b"
             r"|^cargo\s+publish\b|^gem\s+push\b|^helm\s+.*\bpush\b|^gcloud\s+.*\bdeploy\b|^aws\s+.*\bdeploy\b"
             r"|^az\s+.*\bdeploy\b|^git\s+(-C\s+\S+\s+)?push\b")
_INSTALLS = (
    (_r(r"^(python3?\s+-m\s+)?pip3?\s+(install|download)\b|^uv\s+(pip\s+install|add|sync)\b|^poetry\s+(add|install)\b"
        r"|^pipx\s+install\b"), "pypi.org"),
    (_r(r"^(npm\s+(install|i|add|ci)|pnpm\s+(add|install|i)|yarn\s+(add|install)|bun\s+(add|install))\b"),
     "registry.npmjs.org"),
    (_r(r"^cargo\s+(add|install|fetch)\b"), "crates.io"),
    (_r(r"^go\s+(get|install|mod\s+download)\b"), "proxy.golang.org"),
    (_r(r"^(gem\s+install|bundle\s+(install|add))\b"), "rubygems.org"),
    (_r(r"^composer\s+(require|install)\b"), "packagist.org"),
    (_r(r"^dotnet\s+(add\s+package|restore)\b"), "api.nuget.org"),
)
_SYSTEM_PM = _r(r"^(apt(?:-get)?|brew|choco|winget|scoop|apk|dnf|yum)\s+install\b")


def _install_hosts(segment: str) -> list[str] | None:
    """The registry hosts an install command would reach, or None when the segment is not an install."""
    for pattern, default in _INSTALLS:
        if pattern.match(segment):
            return [h.lower() for h in _URL.findall(segment)] or [default]
    if _SYSTEM_PM.match(segment):
        return [_first(segment)]
    return None


def _declared(fence: dict) -> set[str]:
    return {str(r.get("host", "")).lower() for r in fence.get("registries") or [] if isinstance(r, dict)}


def _in_lane(fence: dict, text: str) -> bool:
    for lane in fence.get("lanes") or []:
        try:
            if isinstance(lane, dict) and lane.get("match") and re.search(lane["match"], text):
                return True
        except re.error:
            continue
    return False


def _runner_repos(ctx) -> list[Path]:
    repos = []
    for repo in ctx.fence.get("code_repos") or []:
        if isinstance(repo, dict) and repo.get("path") and repo.get("runner", "container") == "container":
            repos.append((ctx.project / repo["path"]).resolve())
    return repos


def _inside(path: Path, base: Path) -> bool:
    return path == base or base in path.parents


def outside_lane(ctx):
    if ctx.tool in SHELL_TOOLS:
        declared = _declared(ctx.fence)
        cmd_posix = ctx.cmd.replace("\\", "/").lower()
        for seg in ctx.segments:
            if _DEPLOY.search(seg) and not _in_lane(ctx.fence, seg):
                return "a push or deploy outside a declared lane"
            hosts = _install_hosts(seg)
            if hosts is not None:
                bad = [h for h in hosts if not any(h == d or h.endswith("." + d) for d in declared)]
                if bad:
                    return f"an install from {bad[0]}, which fence.yaml does not declare as a registry"
            elif (_first(seg) in _RUNNERS or seg.startswith(("./", ".\\"))) and not _read_only(seg):
                for repo in _runner_repos(ctx):
                    rel = repo.relative_to(ctx.project).as_posix().lower()
                    if _inside(ctx.cwd, repo) or rel in cmd_posix:
                        return "generated code runs outside its declared runner (container)"
    elif _tool(ctx, {"deploy", "publish", "release"}) and not _in_lane(ctx.fence, ctx.tool):
        return "a deploy or publish outside a declared lane"


def _protected(ctx) -> list[Path]:
    paths = [ctx.project / "greenfield" / "fence.yaml", ctx.plugin_root / "packs", ctx.plugin_root / "hooks",
             ctx.plugin_root / "engine" / "gp" / "fence.py", ctx.plugin_root / "engine" / "gp" / "fence_rules.py",
             # retro writes the pack and the project, never the plugin: an installed plugin is a cache an update
             # overwrites, and a second company must not edit the first one's core.
             ctx.plugin_root / "skills", ctx.plugin_root / "agents", ctx.plugin_root / "drivers",
             ctx.plugin_root / "engine" / "gp" / "packcheck.py"]
    if ctx.fence.get("pack_path"):
        paths.append(Path(str(ctx.fence["pack_path"])))
    return [p.resolve() for p in paths]


def fence_edit(ctx):
    guarded = _protected(ctx)
    if ctx.tool in WRITE_TOOLS and ctx.path and any(_inside(ctx.path, g) for g in guarded):
        return "fence.yaml, the pack and the always-pause list change only by the owner's accepted diff"
    if ctx.tool in SHELL_TOOLS:
        text = ctx.cmd.replace("\\", "/").lower()
        marks = ["fence.yaml", *[g.as_posix().lower() for g in guarded[1:]]]
        if any(m in text for m in marks) and any(not _read_only(s) for s in ctx.segments):
            return "a command touches fence.yaml, the pack or the always-pause list"


RULES = (
    ("production", "production anything", production),
    ("outward", "anything a sponsor or third party receives", outward),
    ("irreversible", "irreversible records", irreversible),
    ("scope", "scope: baseline approval and AC changes", scope),
    ("delete-data", "deleting data or evidence", delete_data),
    ("sponsor-data", "sponsor data leaving this machine", sponsor_data),
    ("delete-platform", "deleting an app, repo or project", delete_platform),
    ("credentials", "creating or rotating credentials and tokens", credentials),
    ("shared-env", "changing an environment others share", shared_env),
    ("outside-lane", "a push, deploy, install or run outside its lane", outside_lane),
    ("fence-edit", "fence.yaml, the pack and this list", fence_edit),
)
ALWAYS_PAUSE = tuple(r[0] for r in RULES)
