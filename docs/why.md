# Why charge limits matter

This page covers why capping the charge can slow battery aging, what it costs, and what to expect.

## The story

ThinkPads ship with Lenovo Vantage on Windows, which lets you cap how far the battery charges.
Switch to Ubuntu and you lose that app, even though the firmware still supports the limit. It's the
same story on many Dell, ASUS and HP business laptops: the capability is in the firmware, but the
friendly tooling stays behind on Windows.

## The physics, in one analogy

> Nobody drives a car at the redline all day. Yet we leave laptop batteries pinned at 100% charge
> for years and then wonder why they wear out.

Lithium-ion cells generally age faster when held at a high state of charge. The size of the effect
depends on the cell chemistry and on temperature, and this project does not quantify it. A 60–75%
window avoids holding the cells at high voltage.

## What a charge limit costs

> A charge limit is not a power-saving mode. It limits how full the battery gets.

It does not change CPU frequency or thermal limits. You're managing cell voltage, not throttling
hardware.

What you give up is 25–40% of peak runtime on battery. With a 60–75 window the available charge
varies across that range: somewhere between 60% and 75% of a full battery, instead of 100%. If
you work plugged in and only need the battery now and then (a meeting, a trip), that trade-off
may be acceptable.

## Realistic expectations

- battery-lab does not predict how much longer a charge limit will make your battery last. It
  measures what your battery does, and `trend` fits a line to your own log.
- The only numbers that apply to your battery are the ones in your own log.
- **Existing damage does not reverse.** A limit slows future loss; it doesn't restore lost
  capacity.
- **Heat also accelerates aging.** A hot laptop, or a background process pinning a core for weeks,
  can offset part of the benefit.

> A battery log without temperature only tells half the story.

A charge limit can look perfect on paper while the cells sit in a hot chassis all day. That's why
battery-lab records a temperature with every battery reading. High heat while `Charging` is the
combination to watch. What that temperature does and doesn't measure is covered in
[Known quirks](quirks.md).

## Why it matters beyond your laptop

> A dead battery is often what sends an otherwise healthy laptop to landfill.

The CPU still works. The SSD still works. The battery is the consumable part, and it frequently
decides when the whole machine gets retired. Making it last longer keeps that hardware in use.

---

Next: [How it works](how-it-works.md)

[Documentation index](README.md) · [Project README](../README.md)
