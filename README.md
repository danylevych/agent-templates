# Agent templates

Ready-made agents a member can start from in Discover. Each template sets what the agent
does, which apps and tools it may use, which skills it starts with, and the instruction
files copied into its workspace. The member picks the model.

An admin adds this repository in **Template Sources** (URL, branch or tag, optional read-only
token). obot syncs it and shows every published template to the members its access
policies allow.

## Layout

```
categories.yaml              category ids and labels shown in Discover
schema/template.schema.json  schema of template.yaml
scripts/validate.py          checks every template; run it before a pull request
templates/
  <id>/
    template.yaml            the manifest; its presence is what makes a directory a template
    AGENTS.md                role, workflow and rules
    SOUL.md                  persona and tone
    IDENTITY.md              name, vibe, emoji
    USER.md                  optional; what the agent knows about the people it works for
    icon.svg                 optional; overrides `icon`
```

One directory is one template, and the directory name is its id. Templates are not grouped
in folders by category: the category is a field, so changing it never moves the template or
changes its id.

## template.yaml

```yaml
id: pr-reviewer                  # must equal the directory name
name: Pull Request Reviewer
category: engineering            # an id from categories.yaml
icon: code
description: Reviews Bitbucket pull requests and sums up what changed.
useCases:
  - Summarize a pull request so reviewers can start fast
status: published                # draft templates are visible to admins only

required_tools:
  - mcp.atlassian.read_write     # mcp.<entryKey>.<access>
  - skill.doc                    # skill.<SKILL.md name> of a skill obot already has
```

### required_tools

Each entry is the resource, its name, and for an app the access level:

| Entry | Gives the agent |
|---|---|
| `mcp.<entryKey>.read_only` | the app's tools that only read |
| `mcp.<entryKey>.read_write` | those, and the tools that create or change something; never ones that delete |
| `mcp.<entryKey>.full` | every tool of the app, including ones it adds later |
| `skill.<name>` | the skill with that `SKILL.md` name |

obot sorts an app's tools when it reads the template, the same way the admin and member
screens group them: by what the server declares about a tool, else by the verb in its name
(`get…`, `list…` read; `create…`, `update…` change; `delete…` deletes). A tool whose name
says neither is left to `full`. If an app has no tool of the level asked for, obot lists it
as unresolved rather than handing the agent every tool. An app is listed once, at one level.

### References are keys, not URLs

A template names an app by its MCP catalog `entryKey` and a skill by its `SKILL.md` name.
It never names the repository either comes from, so the same template works in any
installation that has something with that key. obot resolves the keys when a member opens
or uses the template:

| Matches | Result |
|---|---|
| exactly one | used |
| none | the template is shown as needing that app or skill |
| more than one | a configuration error naming the sources; nothing is guessed |

Because templates depend on them, entry keys and skill names are a contract: renaming one
breaks every template that uses it.

A tool the member's policies do not allow is shown as blocked and can be requested.

### Instruction files

`AGENTS.md`, `SOUL.md`, `IDENTITY.md` and `USER.md` (the last is optional) are copied into the agent's workspace when it is
created. The member owns that copy: later changes to the template do not overwrite it.

Do not add `TOOLS.md`. The agent host writes it from the tools the agent really has.

### Skills

A template only picks from the skills obot already has, the ones its skill sources provide
(Skills Management → Skill Sources). It never ships a skill of its own: no `skills/`
directory, no `SKILL.md`. Guidance specific to one template goes in its `AGENTS.md`. If
several templates need the same guidance as a skill, add it to a skill source first.

## Validate

```bash
pip install pyyaml
python3 scripts/validate.py
# also check app keys against an obot MCP catalog:
python3 scripts/validate.py --mcp-catalog ../obot/catalogs/mcp
# and skill names against checked-out skill sources (repeat for each):
python3 scripts/validate.py --skill-source ../skills
```

## Rules

- No secrets in any file. Settings that differ per installation belong in obot, not here.
- Keep `id` stable once a template is published: access policies refer to it.
- Ask before acting: templates that create or change things say so in `AGENTS.md`.
