---
title: "Transitioning from Winamp + Shoutcast DSP to Liquidsoap"
date: 2026-02-28 15:00:00 -0800
categories: [kaad-one]
tags: [winamp, shoutcast, liquidsoap, migration, streaming]
---

I am beginning the kaad-one stream chain transition from Winamp + Shoutcast DSP to Liquidsoap.

## Why migrate now

- The Winamp + DSP workflow has become hard to maintain.
- Liquidsoap gives me better control over inputs, routing, and failover.
- I want the stream stack to be scriptable and reproducible.

## Initial conversion scope

In this first stage, I am focused on getting a basic working pipeline:

1. Define the core Liquidsoap script layout.
2. Recreate the current source chain.
3. Confirm stable output targeting the existing broadcast path.

## What I learned in the first pass

- The migration is more about control and reliability than feature parity.
- Explicit source and output definitions are already making the flow easier to reason about.
- The next risk area is handling edge cases around source loss and reconnect behavior.

## Next steps

- Add clear fallback behavior and reconnection handling.
- Document each config decision in the repo as I go.
- Compare stream behavior against the old chain before full cutover.
