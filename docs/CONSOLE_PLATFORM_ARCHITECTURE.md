# Console Platform Architecture

ZEN is `GRANDMA2_FIRST`, with a future first-class grandMA3 implementation.
Shared layers reason about intake, Song Analysis, Design Intent, Rig Context,
workflow and professional quality. Console-specific layers resolve capability
needs independently:

```text
Lighting Design Intent
 -> Programming Intent / capability needs
 -> Console Capability Model
    -> grandMA2 typed plan / Builder
    -> future grandMA3 typed plan / Builder
```

grandMA3 is not assumed to be grandMA2 with newer syntax. Do not begin an MA3
Builder in this phase, and do not carry an MA2 workaround into MA3 where its
native model may differ. Shared intent must remain free of console commands.
