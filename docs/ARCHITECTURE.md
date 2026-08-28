# MVP architecture

```text
Natural-language request
        ↓
Rule parser → Intent schema → Deterministic command builder
        ↓                         ↓
      Parse error            Safety validator
                                  ↓
                         Preview in floating UI
                                  ↓
                         Operator Execute click
                                  ↓
                      MA2 Telnet TCP client (30000)
```

The MVP never lets an LLM generate and immediately execute an MA command. A
future LLM may propose an `Intent`, but it must still use the same deterministic
builder, validator, preview, and explicit execution path.

The portable runtime resolves `config`, `data`, and `logs` relative to the app
folder. Prototype code uses Python 3.12/Tk; packaging can later replace it with
a single Rust, Go, or C++ executable without changing the control boundary.
