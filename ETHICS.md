# Scope, ethics and dual use

**What this project is:** a research simulator for coordinated multi-agent search under
visibility constraints. It studies how strongly comparisons between search strategies depend
on modelling assumptions, information access and evaluation protocols. Published
close-quarters room-entry techniques serve as one case study because they are well documented
public examples of coordinated visual search.

**What it is not:** not a training tool, not a tactical recommendation, not a validated model
of real operations.

**Deliberate boundaries:**
- The threat model is an abstract probabilistic duel: who sees whom first, and how quickly a
  detected threat stops being a threat. There is no ballistics, no weapon or wounding model,
  and no breaching.
- Techniques are encoded only at the level of public sources (field manuals and public
  training literature), as geometry and timing. Their names denote stylized, unvalidated
  movement models. See `docs/TACTICS.md` for sources and status.
- All results are model-internal and exploratory. Most parameters are free modelling
  choices (`docs/PARAMETERS.md`). Better scores in the model are not evidence that anything is
  better in reality.
- The automatic discovery of new techniques is deliberately deferred and not part of the first
  study.

**Transfer:** the same mathematics applies to civilian problems such as search and rescue,
building inspection, fire service operations and multi-robot exploration. That is the
intended direction of the methodological work.

**AI assistance:** large parts of the code and documentation were written with an AI coding
assistant, and reviews R1-R3 were AI-assisted methodological reviews, not human peer review or
instructor validation. Responsibility for sources, code and claims lies with the author.
