#!/usr/bin/env python3
"""
Simple Mastodon poster for computational biology content.
Run: python mastodon_poster.py
"""

import requests

# Configuration
INSTANCE_URL = "https://mastodon.social"
ACCESS_TOKEN = "hnF4-zOM-VrsMBxHB_wUMo5nMpRz0e6douT0yYBN0IA"

# Example posts - add or modify as needed
POSTS = [
    {
        "title": "Turing Patterns",
        "content": """In 1952, Alan Turing proposed that simple chemical reactions + diffusion could create spots, stripes, and spirals in nature. 70 years later, we're still finding his equations everywhere—from zebrafish stripes to cardiac arrhythmias. Math predicting biology at its finest.

#CompBio #MathBiology #Biophysics"""
    },
    {
        "title": "Kleiber's Law",
        "content": """Why does metabolic rate scale with body mass^0.75 across 20+ orders of magnitude—from bacteria to blue whales? West, Brown & Enquist showed it emerges from fractal-like vascular networks optimized for nutrient delivery. One equation. All of life.

#CompBio #MathBiology #SystemsBiology"""
    },
    {
        "title": "Chaos in Population Dynamics",
        "content": """Robert May showed in 1976 that a simple equation for population growth (x → rx(1-x)) can produce chaos. Lesson: deterministic ≠ predictable. Ecology, epidemiology, and even cardiac dynamics all exhibit this beautiful complexity.

#CompBio #MathBiology #Complexity"""
    },
    {
        "title": "DNA as a Polymer",
        "content": """DNA isn't just a genetic code—it's a semiflexible polymer with a persistence length of ~50 nm. This means physics constrains how it bends, loops, and packs into your nucleus. Information storage meets materials science.

#Biophysics #CompBio #DNA"""
    },
    {
        "title": "Molecular Motors",
        "content": """Kinesin "walks" along microtubules taking 8 nm steps, converting ATP hydrolysis into directed motion with ~50% efficiency. For comparison, car engines are ~25% efficient. Evolution has been optimizing nanomachines for billions of years.

#Biophysics #CellBiology #Evolution"""
    },
    {
        "title": "Levinthal's Paradox",
        "content": """A 100-amino-acid protein has ~10^100 possible conformations. Sampling one per femtosecond would take longer than the age of the universe. Yet proteins fold in milliseconds. The energy landscape must be funneled, not flat. Physics > brute force.

#ProteinFolding #Biophysics #CompBio"""
    },
    {
        "title": "Enzyme Kinetics",
        "content": """The Michaelis-Menten equation (1913) is still biochemistry's workhorse. But single-molecule experiments now show individual enzymes have "memory"—their activity fluctuates over time. The average hides the individual.

#Biochemistry #SingleMolecule #CompBio"""
    },
    {
        "title": "Allosteric Regulation",
        "content": """How does hemoglobin "know" to grab O2 in lungs and release it in tissues? Cooperative binding + allosteric effects. The MWC model (1965) showed proteins are molecular switches, not just catalysts. Molecular computation before computers.

#Biochemistry #Biophysics #MolecularBiology"""
    },
    {
        "title": "The Central Dogma... Isn't",
        "content": """"DNA → RNA → Protein" was the central dogma. Then came reverse transcriptase (RNA → DNA), ribozymes (RNA = catalyst), and now we know ~80% of our genome is transcribed. Biology loves exceptions.

#MolecularBiology #Genetics #CompBio"""
    },
    {
        "title": "Network Motifs",
        "content": """Evolution repeatedly converges on the same network motifs: negative autoregulation for speed, feed-forward loops for filtering noise. Cells are running the same algorithms we'd engineer. Convergent design across 4 billion years.

#SystemsBiology #NetworkBiology #CompBio"""
    },
    {
        "title": "Robustness and Fragility",
        "content": """Bacterial chemotaxis achieves perfect adaptation—response returns to baseline regardless of signal strength. The cost? Specific protein ratios must be exact. Robust to some perturbations, fragile to others. No free lunch.

#SystemsBiology #Microbiology #CompBio"""
    },
    {
        "title": "Stochastic Gene Expression",
        "content": """Identical twins aren't truly identical. Same genome, same environment, different phenotypes. Why? Gene expression is stochastic—individual mRNA molecules matter. Noise isn't just tolerated; sometimes it's exploited.

#Genetics #SystemsBiology #CompBio"""
    },
    {
        "title": "AlphaFold",
        "content": """50 years of the protein folding problem, solved by deep learning in 2020. AlphaFold2 predicts structures with experimental accuracy. But knowing the structure doesn't tell you the function. The next 50 years: dynamics, interactions, design.

#ProteinFolding #AI #CompBio #AlphaFold"""
    },
    {
        "title": "Sequence Space",
        "content": """There are 20^100 possible 100-amino-acid proteins. That's more than atoms in the observable universe. Evolution has sampled a vanishingly small fraction. What functions remain undiscovered in sequence space?

#Evolution #ProteinEngineering #CompBio"""
    },
    {
        "title": "Fisher's Geometric Model",
        "content": """Fisher (1930) showed that beneficial mutations become rarer as organisms approach an optimum, and large mutations are almost always deleterious. Adaptation must proceed in small steps. Geometry constrains evolution.

#Evolution #MathBiology #PopulationGenetics"""
    },
    {
        "title": "Neutral Theory",
        "content": """Most molecular evolution is neutral—not adaptive. Kimura's neutral theory (1968) was controversial but explains why molecular clocks exist. Selection is strong, but drift is everywhere.

#Evolution #PopulationGenetics #MolecularEvolution"""
    },
]


def post_to_mastodon(content: str, visibility: str = "public") -> dict:
    """Post a status to Mastodon."""
    url = f"{INSTANCE_URL}/api/v1/statuses"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    data = {"status": content, "visibility": visibility}

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()


def list_posts():
    """Display all available posts."""
    print("\nAvailable posts:\n")
    for i, post in enumerate(POSTS, 1):
        print(f"  {i:2}. {post['title']}")
    print()


def preview_post(index: int):
    """Preview a post before sending."""
    post = POSTS[index]
    print(f"\n{'='*50}")
    print(f"Title: {post['title']}")
    print(f"{'='*50}")
    print(post['content'])
    print(f"{'='*50}")
    print(f"Character count: {len(post['content'])}/500\n")


def main():
    print("\n" + "="*50)
    print("  Computational Biology Mastodon Poster")
    print("="*50)

    while True:
        list_posts()

        choice = input("Enter post number to preview (or 'q' to quit): ").strip()

        if choice.lower() == 'q':
            print("Goodbye!")
            break

        try:
            index = int(choice) - 1
            if 0 <= index < len(POSTS):
                preview_post(index)

                confirm = input("Post this to Mastodon? (y/n): ").strip().lower()
                if confirm == 'y':
                    try:
                        result = post_to_mastodon(POSTS[index]['content'])
                        print(f"\nPosted successfully!")
                        print(f"URL: {result.get('url', 'N/A')}\n")
                    except requests.exceptions.HTTPError as e:
                        print(f"\nError posting: {e}")
                        print(f"Response: {e.response.text}\n")
                else:
                    print("Post cancelled.\n")
            else:
                print(f"Invalid choice. Please enter 1-{len(POSTS)}.\n")
        except ValueError:
            print("Please enter a valid number.\n")


if __name__ == "__main__":
    main()
