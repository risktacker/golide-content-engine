# Research packet: radiation-induced bit flips

## Core finding

Energetic ionising particles can deposit charge in semiconductor memory or logic and
change a stored bit. This is called a single-event upset (SEU). The device is often
not permanently damaged, so the event is classified as a soft error.

## Claim ledger

| ID | Script-safe claim | Evidence |
|---|---|---|
| C1 | A sufficiently energetic particle interaction can flip a stored 0 to 1 or 1 to 0. | IEEE definition; ESA radiation overview |
| C2 | The particle deposits transient electrical charge in a sensitive semiconductor node. | IEEE definition; ESA Swarm analysis |
| C3 | In orbit, solar protons and galactic cosmic rays contribute to spacecraft upsets. | ESA Swarm; NASA radiation guidance |
| C4 | At ground level, secondary particles produced when cosmic rays strike the atmosphere can contribute to soft errors. | IBM terrestrial cosmic-ray research |
| C5 | A soft error normally does not mean the transistor is permanently broken. | IEEE definition; NASA SCMIT |
| C6 | Error-correcting memory and redundant computation can detect or correct many upsets. | IBM POWER8 RAS; ESA Swarm design discussion |
| C7 | ESA studied sensitive memory across 3,327 days of the three Swarm spacecraft. | ESA Swarm 10-year analysis |
| C8 | The South Atlantic Anomaly was an important source region in the Swarm observations; heavy ions from galactic cosmic rays were another contribution. | ESA Swarm 10-year analysis |

## Primary and authoritative sources

1. ESA, “Swarm vs. space radiation – the first 10 years,” 10 Dec 2024:
   https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Swarm_vs._space_radiation_the_first_10_years
2. NASA Technical Reports Server, “Static Computer Memory Integrity Testing,” 1993:
   https://ntrs.nasa.gov/citations/19940014696
3. IBM Research, “Accelerated testing for cosmic soft-error rate,” IBM Journal of
   Research and Development, 1996:
   https://research.ibm.com/publications/accelerated-testing-for-cosmic-soft-error-rate
4. IBM Research, “Terrestrial cosmic rays,” IBM Journal of Research and Development,
   1996: https://research.ibm.com/publications/terrestrial-cosmic-rays
5. IBM, “POWER8 Processor-Based Systems RAS,” soft-error management section:
   https://www.ibm.com/support/pages/sites/default/files/inline-files/%24FILE/POWER8_RAS_whitepaper_POW03133USEN.PDF
6. IEEE TechNav, “Single Event Upset” definition and engineering overview:
   https://technav.ieee.org/topic/single-event-upset/
7. ESA, “Radiation: satellites' unseen enemy”:
   https://www.esa.int/Enabling_Support/Space_Engineering_Technology/Radiation_satellites_unseen_enemy

## Claims deliberately excluded

- A cosmic ray definitely changed a named election result.
- A cosmic ray definitely caused a named commercial aircraft accident.
- Cosmic rays routinely corrupt ordinary personal computers in a way users notice.

These stories are attractive but causal attribution is disputed or too weak for the
first proof. They may be mentioned only as disputed hypotheses with proper sourcing.

