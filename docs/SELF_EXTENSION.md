# Self-extension foundation

When no Skill exists, a future router may prepare a `SkillProposal`: name,
intent, required MA2 state, safety classification and exact target files. It
does not edit AgentCore and does not produce runnable code automatically.

Only an explicit `install_skill_proposal` approval creates:

```text
skills/installed/<skill-id>/manifest.json
skills/installed/<skill-id>/skill.py
```

The created Skill is disabled and non-executable until a reviewed declarative
implementation path is added. The registry validates manifests, rejects bad or
duplicate ids, and never imports the `skill.py` file. A Skill cannot obtain a
raw socket, password, subprocess permission, safety-policy mutation or an
unapproved MA2 execution API.
