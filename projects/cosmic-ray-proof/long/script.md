# 16:9 script

**Working title:** How Space Can Flip a Bit Inside Your Computer  
**Target:** 4:25–4:50, 145–155 WPM

Inside this memory chip, one switch stores a zero. Nothing touches the computer. No
hacker gets in. The software does exactly what it was written to do. And then the zero
becomes a one.

The chip is not broken. Rewrite the memory and it works normally again. The cause may
have started far above the computer—in space.

Earth is constantly struck by cosmic rays: high-energy particles arriving from beyond
our atmosphere. When one collides with an atom in the air, it can produce a cascade of
secondary particles. Most of this invisible shower passes through the world without
creating a noticeable problem. But electronics operate on extraordinarily small
amounts of charge. In the right place, one particle interaction can matter.

To understand why, imagine a memory cell as a microscopic cup holding electrical
charge. Whether that cup is full or empty represents a one or a zero. This is only a
model—the real circuit uses transistors—but it reveals the weakness.

When an energetic particle or one of its secondary products passes through a sensitive
part of the silicon, it creates a brief trail of charge. If the circuit collects enough
of that charge, the cell can cross its decision threshold. The computer reads the
opposite value. Zero becomes one, or one becomes zero.

Engineers call this a single-event upset. It is also called a soft error because the
hardware is often still healthy. The corrupted value can disappear when the cell is
rewritten. That makes the event especially strange: the machine can be physically
functional and logically wrong.

The risk becomes easier to observe in space. Satellites operate above much of the
atmosphere that protects electronics on the ground. They also pass through regions
where Earth's radiation environment is more intense.

The European Space Agency examined radiation effects recorded by its three Swarm
satellites. These spacecraft have mapped Earth's magnetic field since 2013. Researchers
analysed sensitive onboard memory over 3,327 days and found random bit flips produced
by space radiation. Many events were associated with protons in the South Atlantic
Anomaly—a region where Earth's magnetic field dips closer to the planet. Heavy ions
from galactic cosmic rays made another contribution.

The satellites did not simply fail every time a bit changed. Their systems were
designed to detect and overcome these errors. That points to the most important part
of this story: engineers do not need to stop every particle. They need computers that
can notice when physics has changed the data.

One defence is error-correcting code memory. Alongside the useful data, the system
stores extra information. If a single bit changes, the pattern no longer agrees. The
computer can identify the wrong bit and, in many designs, correct it automatically.
High-reliability systems add other protections: repeated calculations, redundant
hardware, memory scrubbing, and the ability to retry an operation.

These protections matter because soft errors are statistical. One small device might
operate for years without a visible incident. But a satellite constellation, aircraft
electronics, or a data centre contains enormous numbers of sensitive components. Rare
events become engineering problems when the number of opportunities becomes large.

And there is one final twist. The error looks digital—a clean zero becomes a clean
one—but its cause is physical. Software feels abstract, yet every bit ultimately lives
inside matter, under the same universe as everything else.

So when error-correcting memory repairs a flipped bit, the computer is doing more than
checking arithmetic. It is defending information from physics.

