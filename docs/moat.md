## FormationRescue: Our Competitive Moat

FormationRescue's competitive advantage is not simply its use of AI, but its combination of **firsthand competitive dance expertise, specialized formation-repair algorithms, and deterministic validation**. Unlike a general-purpose LLM that can suggest formation changes, FormationRescue provides an end-to-end workflow specifically designed around the challenges dance captains face when a dancer becomes unavailable.

### 1. Advantage Over a Basic LLM Call

A general LLM can recommend new dancer positions, but FormationRescue goes beyond generating suggestions by providing:

- **Real formation import:** Extracts dancer identities, positions, and stage dimensions from supported Sway PDFs.
- **Shape-aware reblocking:** Uses specialized algorithms to repair rows, V formations, diamonds, diagonals, staggered arrangements, and other supported layouts.
- **Constraint-based optimization:** Evaluates candidate repairs using measurable factors such as symmetry, number of positions changed, total displacement, and center preservation.
- **Independent validation:** Uses deterministic Python logic to verify stage boundaries, minimum dancer spacing, consistent dancer assignments, and removal of the unavailable dancer.
- **Visual comparison and review:** Allows captains to compare original and repaired formations, identify moved dancers, and approve or reject suggestions.

Rather than relying on an LLM to decide whether its own output is correct, FormationRescue separates AI interpretation from algorithmic repair and validation.

### 2. Why Another Team Cannot Easily Replicate Our Work in an Afternoon

While another team could build a basic AI-powered formation editor relatively quickly, reproducing our complete workflow would require additional domain understanding, implementation, and testing.

Our system incorporates knowledge of common dance-formation structures, movement tradeoffs, and real choreography constraints. We have also developed specialized handling for Sway PDF exports, including dancer identification, stage-coordinate extraction, and distinguishing current dancer positions from other visual markers.

Additionally, we have implemented multiple repair strategies, objective-based candidate ranking, geometric validation, and automated regression tests. These components represent accumulated engineering work beyond connecting an LLM to a frontend.

### 3. Our Secret Sauce: Firsthand Dance Knowledge

Our team has direct experience with competitive dance and understands the practical challenges of formation changes.

We know that a good repair is not necessarily the most visually symmetrical one. Captains must consider how many dancers need to relearn positions, whether important center placements are preserved, how much movement is introduced, and whether the choreography remains practical.

This domain knowledge informs the constraints, optimization objectives, and evaluation criteria built into FormationRescue. It allows us to translate subjective choreography preferences into measurable computational decisions.

### 4. Building a Long-Term Competitive Advantage

Our strongest opportunity for a sustainable moat is combining our existing algorithms with feedback from real dance captains.

As FormationRescue develops, we could collect permissioned data about which repairs captains accept or reject, what constraints matter most, and which suggestions require manual adjustments.

Over time, this feedback could help us refine our algorithms and develop a specialized dataset of real-world choreography decisions that general-purpose AI models do not automatically possess.

We also plan to strengthen our system with transition-distance validation, choreography-direction constraints, and additional formation types. These improvements would help us move beyond static geometric correctness toward practical performance feasibility.

### Summary

**FormationRescue's moat is the combination of dance-specific expertise, specialized optimization algorithms, independent validation, and an integrated captain-focused workflow.**

A basic LLM can suggest where dancers should stand, but FormationRescue is designed to systematically determine which formation changes satisfy measurable constraints and present those changes for review.

Our long-term advantage is the opportunity to turn real dance-team experience and captain feedback into increasingly accurate, practical, and specialized formation-repair recommendations.

*Current limitation:* FormationRescue validates static geometric constraints but does not yet fully validate transition timing, movement paths, or choreography directions. These are planned improvements rather than existing capabilities.
