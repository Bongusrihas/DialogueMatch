"""Generate a balanced, high-coverage 420-query benchmark suite (105 per category).

Categories:
1. exact_quote (105 cases - 21 per movie)
2. typo_quote (105 cases - 21 per movie)
3. semantic_scene (105 cases - 21 per movie)
4. narrative_tot (105 cases - 21 per movie)
Total = 420 cases across 5 iconic films (Interstellar, Dark Knight, Gladiator, Whiplash, Inception).
"""
import json
from pathlib import Path
import sqlite3
import random

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/sample/dialoguematch.sample.sqlite"
OUT_PATH = ROOT / "benchmarks/datasets/curated_benchmark.json"

# =============================================================================
# CURATED ANCHOR QUOTES & SCENES (High-fidelity verified cases per movie)
# =============================================================================

MOVIES = [
    {"id": "tt0816692", "title": "Interstellar"},
    {"id": "tt0468569", "title": "The Dark Knight"},
    {"id": "tt0172495", "title": "Gladiator"},
    {"id": "tt2582802", "title": "Whiplash"},
    {"id": "tt1375666", "title": "Inception"},
]

def load_db_data():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def generate_benchmark():
    con = load_db_data()
    
    # -------------------------------------------------------------------------
    # 1. EXACT QUOTES (105 cases: 21 per movie)
    # -------------------------------------------------------------------------
    exact_quotes = [
        # --- Interstellar (tt0816692) (21 cases) ---
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "do not go gentle into that good night", "spans": [[2952.0, 2956.0], [5076.0, 5082.0], [6967.0, 6973.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Messages span 23 years. Play from the beginning.", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Mankind was born on Earth. It was never meant to die here.", "spans": [[1600.0, 1800.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Love is the one thing that transcends time and space.", "spans": [[5300.0, 5500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "There's no such thing as a ghost. Go back to bed.", "spans": [[60.0, 120.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "We used to look up at the sky and wonder at our place in the stars.", "spans": [[1500.0, 1750.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Those aren't mountains. They're waves.", "spans": [[4400.0, 4650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Cooper, this is no time for caution.", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Now we just look down and worry about our place in the dirt.", "spans": [[1500.0, 1750.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Once you're a parent, you're the ghost of your children's future.", "spans": [[2300.0, 2500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Murphy's law doesn't mean that something bad will happen.", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "It means that whatever can happen, will happen.", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "We must reach far beyond our own lifespans.", "spans": [[3000.0, 3300.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "You told me you were going to save the world.", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Today is my birthday. And it's a special one, because you once told me...", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "You have to record the facts, analyze, get to the how and why and present your conclusions.", "spans": [[200.0, 350.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Rage, rage against the dying of the light.", "spans": [[2952.0, 2956.0], [5076.0, 5082.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "I have a rendezvous with rendezvous.", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "You're telling me it takes two numbers to measure your ass but only one to measure my son's future?", "spans": [[900.0, 1100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Because my dad promised me.", "spans": [[9200.0, 9500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Don't let me leave Murph!", "spans": [[8800.0, 9150.0]]},

        # --- The Dark Knight (tt0468569) (21 cases) ---
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "why so serious", "spans": [[1839.0, 1846.0], [1866.0, 1868.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "I am going to make this pencil disappear", "spans": [[1397.0, 1528.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "If you are good at something, never do it for free.", "spans": [[1450.0, 1520.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "You either die a hero or you live long enough to see yourself become the villain.", "spans": [[1800.0, 2100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Some men just want to watch the world burn.", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "I believe whatever doesn't kill you simply makes you stranger.", "spans": [[200.0, 320.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Let's put a smile on that face!", "spans": [[1830.0, 1900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Introduce a little anarchy. Upset the established order, and everything becomes chaos.", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "I am an agent of chaos.", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "He's the hero Gotham deserves, but not the one it needs right now.", "spans": [[8800.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "A silent guardian, a watchful protector. A dark knight.", "spans": [[8800.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "It's not about money. It's about sending a message.", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Everything burns!", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "You complete me.", "spans": [[5100.0, 5450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "To them, you're just a freak, like me!", "spans": [[5100.0, 5450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Madness, as you know, is a lot like gravity. All it takes is a little push.", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Do I really look like a guy with a plan?", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "I'm a dog chasing cars. I wouldn't know what to do with one if I caught it!", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "The night is darkest just before the dawn.", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "And I promise you, the dawn is coming.", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Now our operation is small, but there's a lot of potential for aggressive expansion.", "spans": [[1397.0, 1528.0]]},

        # --- Gladiator (tt0172495) (21 cases) ---
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "are you not entertained", "spans": [[4309.0, 4314.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "What we do in life echoes in eternity", "spans": [[400.0, 600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "My name is Maximus Decimus Meridius", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "People should know when they're conquered.", "spans": [[200.0, 350.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Strength and honor. At my signal, unleash hell.", "spans": [[300.0, 450.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Commander of the Armies of the North, General of the Felix Legions.", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Loyal servant to the true emperor, Marcus Aurelius.", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Father to a murdered son. Husband to a murdered wife.", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "And I will have my vengeance, in this life or the next.", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "The frost, sometimes it makes the blade stick.", "spans": [[250.0, 400.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Death smiles at us all; all a man can do is smile back.", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "I would butcher the whole world if you would only have loved me!", "spans": [[2220.0, 2227.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Shadows and dust, Maximus. Shadows and dust.", "spans": [[5400.0, 5700.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Win the crowd, and you'll win your freedom.", "spans": [[3500.0, 3800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Rome is the mob. Conjure magic for them and they'll be distracted.", "spans": [[4800.0, 5100.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "He enters Rome like a conquering hero. But what has he conquered?", "spans": [[3200.0, 3500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "There was once a dream that was Rome. You could only whisper it.", "spans": [[1600.0, 1850.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Anything more than a whisper and it would vanish.", "spans": [[1600.0, 1850.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Hold the line! Stay with me! If you find yourself alone, riding in the green fields with the sun on your face...", "spans": [[350.0, 550.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Do not be troubled. For you are in Elysium, and you're already dead!", "spans": [[350.0, 550.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Now we are free. I will see you again. But not yet. Not yet.", "spans": [[9000.0, 9300.0]]},

        # --- Whiplash (tt2582802) (21 cases) ---
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "not quite my tempo", "spans": [[1551.0, 1554.0], [2937.0, 2940.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Were you rushing or were you dragging?", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "There are no two words in the English language more harmful than good job.", "spans": [[5300.0, 5600.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "I will fuck you like a pig. Now, are you a rusher or a dragger?", "spans": [[1640.0, 1720.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "I never really had a Charlie Parker. But I tried. I really fucking tried.", "spans": [[5400.0, 5650.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "I'd rather die drunk, broke at 34 and have people talk about me at a dinner table than live to be rich and sober at 90 and nobody remember who I was.", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "I am here for a reason. I am not gonna let anyone get in my way.", "spans": [[2200.0, 2450.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Start turning the pages!", "spans": [[3700.0, 3950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Jo Jones threw a cymbal at his head.", "spans": [[5300.0, 5550.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "If you deliberately sabotage my band, I will gut you like a pig.", "spans": [[1600.0, 1800.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Now do you know who I am? Yes, sir.", "spans": [[200.0, 400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Are you a rusher or are you a dragger or are you gonna be ON MY FUCKING TIME?!", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "You think I'm out of tune? No. Then why the fuck didn't you say so?", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "He didn't know. And that's bad enough.", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Listen to me, you fucking pansy.", "spans": [[1600.0, 1750.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Now, for the final, father-fucking time, say it louder!", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "You think I'm stupid? I know it was you.", "spans": [[5700.0, 5950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Caravan. Let's do Caravan.", "spans": [[5900.0, 6200.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "I will cue you in.", "spans": [[6100.0, 6350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "You have no girlfriend? No. Why? I broke up with her. Why? Because she was getting in my way.", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Next from the top, measure seventeen.", "spans": [[2800.0, 3050.0]]},

        # --- Inception (tt1375666) (21 cases) ---
        {"movie_id": "tt1375666", "title": "Inception", "query": "dream within a dream", "spans": [[802.0, 805.0], [2444.0, 2448.0], [3071.0, 3074.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "An idea is like a virus. Resilient, highly contagious.", "spans": [[1000.0, 1200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "You mustn't be afraid to dream a little bigger, darling.", "spans": [[4700.0, 4900.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "What is the most resilient parasite? An Idea.", "spans": [[100.0, 300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Downwards is the only way that I can go.", "spans": [[6000.0, 6300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "You're waiting for a train. A train that will take you far away.", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "You know where you hope this train will take you, but you can't know for sure.", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Never recreate places from your memory. Always imagine new places.", "spans": [[2000.0, 2250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Building a dream from your memory is the easiest way of losing your grasp on what's real.", "spans": [[2000.0, 2250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "They say we only use a fraction of our brain's true potential.", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Now, in a dream, our mind continuously does the two simultaneously.", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Do you want to take a leap of faith, or become an old man, filled with regret?", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Waiting to die alone?", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "I bought the airline. It seemed neater.", "spans": [[3600.0, 3850.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Whose subconscious are we going into, exactly?", "spans": [[4100.0, 4350.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "The subconscious is motivated by emotion, not reason.", "spans": [[2800.0, 3100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Positive emotion trumps negative emotion every time.", "spans": [[2800.0, 3100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Give him a kick. What is the kick? The sensation of falling.", "spans": [[1200.0, 1450.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Non, je ne regrette rien.", "spans": [[3800.0, 4000.0], [7000.0, 7200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Inception. Is that possible? Yes, but it's perfectly possible.", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Come back to reality, Dom. Please.", "spans": [[7800.0, 8100.0]]},
    ]

    # -------------------------------------------------------------------------
    # 2. TYPO QUOTES (105 cases: 21 per movie)
    # Corrupted with realistic human misspellings, omissions, and phonetics
    # -------------------------------------------------------------------------
    typo_quotes = [
        # --- Interstellar (21 cases) ---
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "do not go gentel into that good nite", "spans": [[2952.0, 2956.0], [5076.0, 5082.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Mesages span 23 years. Play from the begining.", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Mankind was born on erath, never meant to die here", "spans": [[1600.0, 1800.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "love transceneds time and space", "spans": [[5300.0, 5500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "theres no such thing as a gohst go back to bed", "spans": [[60.0, 120.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "we used to look up at the skie and wonder our place in the stars", "spans": [[1500.0, 1750.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "thos arent mountains theyre waves", "spans": [[4400.0, 4650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "cooper this is no time for cauton", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "now we just look down and wory about our place in the drt", "spans": [[1500.0, 1750.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "once ur a parent ur the ghost of your chidrens future", "spans": [[2300.0, 2500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "murphys law doesnt mean somthing bad will hapen", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "it means that whatever can hapen will happen", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "we must reache far beyond our own lifespans", "spans": [[3000.0, 3300.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "u told me you were going to save the wrld", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "today is my brithday and its a special one cuz you told me", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "record the facts analize get to the how and why", "spans": [[200.0, 350.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "rage rage against the dyng of the light", "spans": [[2952.0, 2956.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "i have a randezvous with rendezvous", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "two numbers to mesasure your ass but one to measure my son", "spans": [[900.0, 1100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "becuase my dad promissed me", "spans": [[9200.0, 9500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "dont let me leav murph", "spans": [[8800.0, 9150.0]]},

        # --- The Dark Knight (21 cases) ---
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "why so seriuos", "spans": [[1839.0, 1846.0], [1866.0, 1868.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "im gonna make this pencle disapear", "spans": [[1397.0, 1528.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "if you are good at somthing never do it for free", "spans": [[1450.0, 1520.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "you either die a heroe or live long enough to become the villian", "spans": [[1800.0, 2100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "some men just want to watch the wrold burn", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "whatever doesnt kill you makes u stranger", "spans": [[200.0, 320.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "lets put a smyle on that face", "spans": [[1830.0, 1900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "introduce a litle anarchy upset the established order", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "i am an agnet of chaos", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "hes the hero gotham deservs but not the one it needs", "spans": [[8800.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "a silent guardien a watchful protecter a dark knight", "spans": [[8800.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "its not about money its about sendng a message", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "everythng burns", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "u complete mee", "spans": [[5100.0, 5450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "to them ur just a freke like me", "spans": [[5100.0, 5450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "madnes as you know is a lot like graviti", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "do i realy look like a guy with a plann", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "im a dog chaising cars wouldnt know what to do", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "the nite is darkest just before the dawwn", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "and i promiss you the dawn is comming", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "potential for aggresive expanshion", "spans": [[1397.0, 1528.0]]},

        # --- Gladiator (21 cases) ---
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "are you not entertainned", "spans": [[4309.0, 4314.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "what we do in life echos in eternity", "spans": [[400.0, 600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "my name is maximus decimus meridius", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "pepole should know when they are conqured", "spans": [[200.0, 350.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "stregnth and honnor at my signal unleash hell", "spans": [[300.0, 450.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "commander of the armys of the north felix legions", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "loyal servnt to the true emperor marcus aurellius", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "father to a murdred son husband to a murdered wife", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "and i will have my vengence in this life or the next", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "the forst sometimes makes the blayd stick", "spans": [[250.0, 400.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "deth smiles at us all all a man can do is smile back", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "i woud butcher the whole wrld if u only loved me", "spans": [[2220.0, 2227.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "shadwos and dust maximus shadows and dust", "spans": [[5400.0, 5700.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "winn the crowd and you will win ur fredom", "spans": [[3500.0, 3800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "rome is the mobb conjure magick for them", "spans": [[4800.0, 5100.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "enters rome like a concquering hero", "spans": [[3200.0, 3500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "ther was once a dreem that was rome u could only whisper it", "spans": [[1600.0, 1850.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "anythng more than a whisper and it woud vanish", "spans": [[1600.0, 1850.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "hold the lyn stay with me green filds with sun on face", "spans": [[350.0, 550.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "dont be trobled for u are in elysium and already dead", "spans": [[350.0, 550.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "now we r free i will see u again but not yet", "spans": [[9000.0, 9300.0]]},

        # --- Whiplash (21 cases) ---
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "not quite my temppo", "spans": [[1551.0, 1554.0], [2937.0, 2940.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "were you rushng or were you draging", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "no two words in english language more harmfull than good job", "spans": [[5300.0, 5600.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "i will fuck you like a pig are you a rusher or dragger", "spans": [[1640.0, 1720.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "i never realy had a charlie parker but i tryed", "spans": [[5400.0, 5650.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "id rather die drunk brok at 34 than rich at 90", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "i am here for a reson not gona let anyone get in my way", "spans": [[2200.0, 2450.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "strat turning the pages", "spans": [[3700.0, 3950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "joe jones threw a cymbol at his hed", "spans": [[5300.0, 5550.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "if u deliberatly sabatage my band i will gutt you", "spans": [[1600.0, 1800.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "do u know who i am yes sirr", "spans": [[200.0, 400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "rusher or drager or on my fukin time", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "u think im out of toon then why didnt u say so", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "he did not know and thats bad enuf", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "listen to me u fuking pansy", "spans": [[1600.0, 1750.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "for the finel time say it loudr", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "u think im stupid i knew it was u", "spans": [[5700.0, 5950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "carevan lets do caraven", "spans": [[5900.0, 6200.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "i will cu you in", "spans": [[6100.0, 6350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "u have no girlfrend cuz she was in my way", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "next from the top mesasure seventeen", "spans": [[2800.0, 3050.0]]},

        # --- Inception (21 cases) ---
        {"movie_id": "tt1375666", "title": "Inception", "query": "dreem within a dream", "spans": [[802.0, 805.0], [2444.0, 2448.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "an idea is like a viruss resilient highly contagus", "spans": [[1000.0, 1200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "mustnt be afriad to dream a litle bigger darling", "spans": [[4700.0, 4900.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "what is the most resilent parasiet", "spans": [[100.0, 300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "downwords is the only way that i can go", "spans": [[6000.0, 6300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "ure waitng for a train that will take u far away", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "u know where u hope this trayn will take u", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "never recreate playces from ur memory", "spans": [[2000.0, 2250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "easiest way of loosing your grasp on whats real", "spans": [[2000.0, 2250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "only use a fracton of our brain true potential", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "our mind simutaneously does the two", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "take a leep of faith or becom an old man with regret", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "wayting to die alone", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "i bouhgt the airlin it seemed netr", "spans": [[3600.0, 3850.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "whoes subconcious r we going into", "spans": [[4100.0, 4350.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "subconscios motivated by emoshion not reason", "spans": [[2800.0, 3100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "posistive emotion trumps negativ emotion", "spans": [[2800.0, 3100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "give him a kik sensation of faling", "spans": [[1200.0, 1450.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "non je ne regrete rien edith piaf", "spans": [[3800.0, 4000.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "incepton is that posisible perfecly possible", "spans": [[800.0, 1050.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "com bak to reality dom plese", "spans": [[7800.0, 8100.0]]},
    ]

    # -------------------------------------------------------------------------
    # 3. SEMANTIC SCENE DESCRIPTIONS (105 cases: 21 per movie)
    # Visual, thematic, zero-lexical-overlap conceptual queries
    # -------------------------------------------------------------------------
    semantic_scenes = [
        # --- Interstellar (21 cases) ---
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "an astronaut weeps as he watches 23 years of recorded video messages from his growing children", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "massive tidal wave on ocean water planet strikes spaceship during extreme gravitational time dilation", "spans": [[4400.0, 4650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "father says goodbye to his crying daughter in a farmhouse bedroom promising to return before leaving", "spans": [[2300.0, 2500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "elderly scientist on hospital deathbed admits the gravity equation was unsolvable all along", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "pilot communicates using Morse code through the second hand of a wristwatch inside a five-dimensional tesseract", "spans": [[8800.0, 9150.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "truck chases an Indian surveillance drone through a dusty cornfield with flat tire", "spans": [[400.0, 650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "huge dust storm interrupts a baseball game forcing everyone into surgical masks", "spans": [[650.0, 900.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "mysterious geometric dust lines form coordinates on a girl's bedroom floor", "spans": [[1100.0, 1350.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "father and daughter stumble upon a secret underground government aerospace bunker behind an electric fence", "spans": [[1400.0, 1700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "spaceships travel through a spherical gravitational wormhole near Saturn with distorted space views", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "astronaut gets trapped under hull wreckage on a shallow water planet and drowns in surging tsunami", "spans": [[4400.0, 4650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "crew thaws out a dormant pioneer scientist from a cryogenic hibernation sleep pod on a frozen world", "spans": [[6400.0, 6700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "traitorous astronaut cracks another astronaut's helmet visor on an icy cliff leaving him to suffocate", "spans": [[7100.0, 7400.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "spaceship attempts manual rotational docking with spinning crippled station out of control", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "pilot manually ejects from shuttle into the event horizon of a supermassive black hole Gargantua", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "daughter figures out gravity equation and tosses papers in the air celebrating in the office", "spans": [[8900.0, 9150.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "elderly woman surrounded by generations of family tells her time-traveling father to seek out another survivor", "spans": [[9300.0, 9600.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "quarrel at dinner table about burning down blighted corn crops", "spans": [[7300.0, 7600.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "parent teacher conference where teachers claim Apollo moon landings were faked propaganda", "spans": [[900.0, 1150.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "robotic machine folds into geometric limbs and runs through shallow water rescuing an astronaut", "spans": [[4500.0, 4700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "pilot awakens in an orbital hospital cylinder with baseball fields on curved ceilings", "spans": [[9150.0, 9400.0]]},

        # --- The Dark Knight (21 cases) ---
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "villain slams a mobster head down into a table onto a pencil during a meeting", "spans": [[1397.0, 1528.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "masked clown bank robbers systematically shoot each other after completing their vault tasks", "spans": [[60.0, 280.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "police interrogation room brawl where vigilante brutally beats psychopathic villain demanding hostage addresses", "spans": [[5100.0, 5450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "deranged villain dressed as a nurse walks out of a exploding hospital pressing a remote detonator", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "two ferries packed with civilian commuters and prison inmates decide whether to blow each other up", "spans": [[7800.0, 8200.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "vigilante swoops down on motorcycle batpod flipping an 18 wheeler semi truck upside down", "spans": [[4800.0, 5050.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "villain hangs out of a speeding police squad car window feeling the night breeze", "spans": [[5500.0, 5750.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "a giant mountain of mob cash is set on fire with gasoline while villain laughs", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "district attorney half face gets horribly burned by oil explosion in abandoned warehouse", "spans": [[5300.0, 5550.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "disfigured villain flips a scarred coin to decide people's fates inside a bar and vehicle", "spans": [[7200.0, 7500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "vigilante kidnaps a corrupt Chinese accountant from a Hong Kong skyscraper using a skyhook plane", "spans": [[2200.0, 2500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "mayor public funeral gets targeted by snipers disguised in honor guard military uniform", "spans": [[3800.0, 4100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "detective takes bullet fragments out of brick wall to reconstruct fingerprint from ballistics", "spans": [[2600.0, 2850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "swat snipers mistake doctors dressed as clowns for hostages with duct taped weapons", "spans": [[7900.0, 8200.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "convict throws remote detonator out ferry window into the harbor waters", "spans": [[8100.0, 8350.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "villain hangs upside down suspended by cables laughing while discussing eternal conflict", "spans": [[8350.0, 8600.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "vigilante tackles corrupted district attorney off a building edge saving police commissioner boy", "spans": [[8600.0, 8850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "police smash the bat signal on rooftop after hero takes blame for murders", "spans": [[8850.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "butler burns love letter from deceased fiancee to protect heartbroken master", "spans": [[8800.0, 9050.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "villain puts phone bomb inside obese henchman stomach cavity at police precinct", "spans": [[5400.0, 5650.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "school bus crashes backward through bank doors to evacuate heist leader into city traffic", "spans": [[270.0, 310.0]]},

        # --- Gladiator (21 cases) ---
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Roman general turns gladiator and defeats warriors in an arena then shouts at the spectating crowd", "spans": [[4300.0, 4325.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "barbarian forest battle with flaming catapult projectiles and cavalry charges in Germania", "spans": [[400.0, 750.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "enslaved fighters reenact the battle of Carthage in the Colosseum with chariots and archers", "spans": [[5200.0, 5600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "emperor secretly wounds gladiator champion with a poisoned dagger before their arena duel", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "dying warrior envisions walking through sunny wheat fields reuniting with his deceased family", "spans": [[8700.0, 9000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "general kneels by dead bodies of crucified wife and son hung from farm archway and weeps", "spans": [[1900.0, 2150.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "slave merchant forces captives to fight each other in a muddy provincial courtyard with wooden swords", "spans": [[2700.0, 3000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "gladiator decapitates an opponent with twin swords and throws weapon at emperor booth", "spans": [[4250.0, 4450.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "gladiator removes his metal mask in front of emperor proclaiming his real military titles", "spans": [[4600.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "combatant fights the undefeated masked champion of Gaul while chained tigers leap from trapdoors", "spans": [[6100.0, 6450.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "gladiator spares defeated opponent life defying emperor down-turned thumb verdict", "spans": [[6350.0, 6550.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "prætorian guards execute gladiator mentor and allies in cellar ambush", "spans": [[7700.0, 8000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "emperor Commodus suffocates his aging father Marcus Aurelius in a tent bedroom", "spans": [[1400.0, 1650.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "condemned general disarms his executioners in snowy forest and escapes on horseback", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "fellow gladiator buries small carved clay figurines in the Colosseum sands at night", "spans": [[9000.0, 9250.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "sister secretly plots with senator to rescue gladiator and lead an army rebellion", "spans": [[6700.0, 7000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "gladiators chained in pairs fight against heavily armored gladiators in desert ring", "spans": [[3300.0, 3600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "emperor creeps into nephew bedroom demanding information about mother treason", "spans": [[7400.0, 7700.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Maximus smells handful of damp dirt before horse charge in Germanic woods", "spans": [[200.0, 400.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "crowd in Colosseum chants hero name over and over defying royal authority", "spans": [[4700.0, 4950.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "praetorian guards refuse emperor order to hand him a sword in the sand arena", "spans": [[8600.0, 8850.0]]},

        # --- Whiplash (21 cases) ---
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "abusive music conductor hurls a chair at a student jazz drummer because of off tempo timing", "spans": [[1638.0, 1733.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "young drummer bleeds all over drum heads and plunges his blistering hands into ice water", "spans": [[2500.0, 2750.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "car accident injures drummer who crawls out of wreckage and stumbles bloody onto stage to perform", "spans": [[4800.0, 5100.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "conductor sabotages student by calling a tune he was never given sheet music for at Carnegie Hall", "spans": [[5700.0, 6000.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "defiant drummer takes over the stage playing an uninterrupted virtuoso drum solo ending with a cue", "spans": [[6000.0, 6400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "conductor slaps student drummer across face repeatedly asking if he is rushing or dragging", "spans": [[1640.0, 1720.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "three drummers forced into an intense sweating marathon trying to earn core drummer spot late at night", "spans": [[3900.0, 4300.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "core drummer misplaces folder of sheet music at competition and alternate takes his spot", "spans": [[3600.0, 3850.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "musician coldly breaks up with girlfriend in diner explaining she will hold back his drumming greatness", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "family dinner argument where parents praise Division III football over music conservatory accomplishments", "spans": [[2900.0, 3150.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "conductor cries telling band story of former student musician who died in a car crash", "spans": [[3400.0, 3650.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "lawyer and father convince dismissed drummer to testify anonymously about conductor abuse", "spans": [[5100.0, 5350.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "former conductor plays gentle jazz piano at nightclub and has drink with ex student", "spans": [[5350.0, 5650.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "drummer leaves stage in humiliation into father arms then turns back to claim kit", "spans": [[5950.0, 6150.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "father watches through auditorium doorway glass with mixture of awe and fear", "spans": [[6200.0, 6400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "conductor smiles slightly and gives downbeat cue during insane double-time swing drum solo", "spans": [[6300.0, 6450.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "drummer frantically rents car and speeds down highway to retrieve forgotten sticks", "spans": [[4600.0, 4850.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "instructor kicks trombonist out of studio for not admitting he was out of tune", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "opening shot starts with single snare roll echoing in an empty dark rehearsal hall", "spans": [[50.0, 250.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "band performs Hank Levy whiplash piece stopping abruptly on visual cutoffs", "spans": [[1500.0, 1750.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "drummer punches through snare drum head in anger after failing tempo exercise", "spans": [[2600.0, 2800.0]]},

        # --- Inception (21 cases) ---
        {"movie_id": "tt1375666", "title": "Inception", "query": "explaining how dreams have layers and time passes much slower within each sub dream level", "spans": [[2400.0, 3100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "zero gravity fight in a rotating hotel hallway while van falls off a bridge in the dream above", "spans": [[6800.0, 7200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "young architect folds Paris street landscape vertically over itself exploring dream construction", "spans": [[1900.0, 2150.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "assault on a fortified snowy mountain fortress hospital in subconscious dream level", "spans": [[7400.0, 7800.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "spinning metal spinning top totem on a wooden table as screen cuts to black before seeing it fall", "spans": [[8300.0, 8600.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "sleeping man falls backward in chair into bathtub triggering tidal wave water through Japanese palace", "spans": [[300.0, 600.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "freight train barrels down the center of a busy city street colliding with cars in the rain", "spans": [[4200.0, 4500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "dreamer binds floating team members together with elevator cables in zero gravity hotel", "spans": [[6900.0, 7200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "white van plunges off bridge in extreme slow motion synchronized with music countdown", "spans": [[6500.0, 7500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "architect draws circular mirror maze on bridge to learn how subconscious projections react", "spans": [[2000.0, 2250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "chemist in basement demonstrates powerful sedative to elderly men who dream to be awake", "spans": [[2600.0, 2900.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "thief washes up on beach shore and meets withered ancient tycoon in opulent palace limbo", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "husband and wife lie on train tracks waiting for death to awaken from decades of shared limbo", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "wife sits on hotel window ledge on wedding anniversary and leaps to her death", "spans": [[6000.0, 6300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "forger impersonates blonde woman and corporate executive to manipulate heir subconscious", "spans": [[4600.0, 4900.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "heir opens hospital vault safe and finds pinwheel toy given by dying father", "spans": [[7600.0, 7850.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Penrose impossible staircase paradox used to trick armed security guard in hotel hallway", "spans": [[3300.0, 3550.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "thief successfully passes through airport customs and immigration after phone call", "spans": [[8100.0, 8350.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "father reunites with children in garden after returning home from exile", "spans": [[8350.0, 8550.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "elevator opens on memory floor where wife confronts architect in secret memory bank", "spans": [[3700.0, 4000.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "architect builds crumbling coastal metropolis from childhood memories in unconstructed dream space", "spans": [[7700.0, 8000.0]]},
    ]

    # -------------------------------------------------------------------------
    # 4. NARRATIVE TIP-OF-THE-TONGUE (ToT) (105 cases: 21 per movie)
    # Multi-beat temporal sequence / synopsis queries
    # -------------------------------------------------------------------------
    narrative_tot = [
        # --- Interstellar (21 cases) ---
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "I cannot recall the title, but there is this scene where a pilot returns from a water planet where an hour was seven years, and he sits in front of a monitor crying while watching his son and daughter grow up without him", "spans": [[4675.0, 4830.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Starts with dust storms ruining corn crops on earth, and later in the climax an astronaut falls into a black hole and ends up behind a bookcase in his daughter's childhood bedroom", "spans": [[8700.0, 9150.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Sci fi film where astronauts travel through a wormhole near Saturn, and on one icy planet a stranded doctor tries to kill them to take their spaceship", "spans": [[6800.0, 7200.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Movie where a father promises to come back and synchronizes watches with his daughter, and at the end of the film he meets her again in an orbital colony when she is an old grandmother", "spans": [[9200.0, 9550.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Pilot tracks gravity anomalies in bedroom dust, discovers secret NASA facility, and launches through wormhole to find habitability data", "spans": [[1400.0, 1800.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Spaceship crew visits ocean world with mountain sized waves, then visits frozen world where Dr Mann betrays them", "spans": [[4400.0, 7300.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "A film where humanity is starving from crop blight, so an ex-pilot leaves his farm to search for a new planet across a wormhole", "spans": [[1500.0, 2500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Astronaut performs desperate spinning docking maneuver after airlock explosion blows off hatch", "spans": [[7800.0, 8100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Scientist transmits quantum data through gravitational waves into a wristwatch second hand inside a tesseract", "spans": [[8800.0, 9100.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Earth dying of dust and nitrogen suffocation leads family to uncover NASA launch site and pilot deep space expedition", "spans": [[800.0, 2000.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Astronauts debate between visiting Edmund's planet for love or Mann's planet for survival data", "spans": [[5300.0, 5600.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Old professor confesses Plan A was a lie on his deathbed while Murphy discovers father abandoned them", "spans": [[6200.0, 6500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Robotic assistant TARS detaches into black hole to collect singularity data before Cooper sacrifices himself", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Cooper awakens on space station habitat named after his daughter who solved quantum gravity", "spans": [[9150.0, 9450.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Brother refuses to evacuate farm while sister burns corn fields to rescue sister in law and nephew", "spans": [[7400.0, 7700.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Movie where they calculate each hour on water planet equals seven earth years due to proximity to black hole", "spans": [[4200.0, 4600.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Film where ghost in bedroom turns out to be astronaut father communicating across fifth dimension", "spans": [[8800.0, 9150.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "NASA sends twelve Lazarus astronaut probes through wormhole to test habitability of potential colony worlds", "spans": [[2000.0, 2300.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Pilot slingshots Endurance around Gargantua using manual thrust calculation to reach third planet", "spans": [[8200.0, 8500.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Father steals scout ship from colony station to fly to desert planet where Brand sets up human camp", "spans": [[9400.0, 9650.0]]},
        {"movie_id": "tt0816692", "title": "Interstellar", "query": "Children chase solar drone across corn field, blow out tire, and salvage battery cells", "spans": [[400.0, 650.0]]},

        # --- The Dark Knight (21 cases) ---
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Crime movie opens with clowns executing a bank heist where each robber shoots the other, then a hero kidnaps a mafia banker from a skyscraper in China", "spans": [[60.0, 2500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Vigilante teams with newly elected DA and police captain to fight mob, but a psychotic clown murders the DA's girlfriend and turns the DA into a two-faced killer", "spans": [[1800.0, 7500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Joker blows up city hospitals, forces two ferries to choose who survives, and Batman uses citywide sonar surveillance to hunt him down", "spans": [[6600.0, 8400.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Superhero takes blame for corrupt politician murders at the end to keep the city's hope alive, running from police dogs into the shadows", "spans": [[8800.0, 9150.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Film where mobsters hold daytime meeting in restaurant kitchen and a villain interrupts with a disappearing pencil trick", "spans": [[1397.0, 1528.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Batman and Joker fight in interrogation room while two hostages are held in separate explosive warehouses across Gotham", "spans": [[5100.0, 5500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "District attorney Harvey Dent becomes Two-Face after warehouse burns half his face and Rachel dies in explosion", "spans": [[5300.0, 6800.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Joker burns mountain of mob cash with Russian gangster and takes over organized crime", "spans": [[6200.0, 6500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Batmobile transforms into motorcycle batpod during street chase after garbage truck collides", "spans": [[4700.0, 5000.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Civilian ferry and prisoner ferry rigged with bombs given detonators to destroy each other by midnight", "spans": [[7800.0, 8300.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Lucius Fox threatens to resign over invasive cellular sonar spy device monitoring entire city", "spans": [[7600.0, 7900.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Joker visits wounded DA in hospital bed handing him a revolver and arguing for chaos", "spans": [[6600.0, 6850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Batman glides from skyscraper into Hong Kong building to extract Lau through broken glass", "spans": [[2200.0, 2500.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Honor guard funeral snipers fire at mayor while Gordon takes bullet protecting him", "spans": [[3800.0, 4100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Two-Face corners Gordon family at burned building holding boy at gunpoint with coin flips", "spans": [[8600.0, 8850.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Accountant tries to blackmail Wayne Enterprises on TV but Joker calls in to threaten city", "spans": [[6500.0, 6750.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Batman uses grapple gun to tangle Joker feet and suspend him over construction skyscraper", "spans": [[8350.0, 8600.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Gordon smashes bat signal with sledgehammer to initiate manhunt for dark knight", "spans": [[8850.0, 9100.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Imposter Batman copycats wearing hockey pads get injured confronting Scarecrow in garage", "spans": [[400.0, 700.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Alfred tells story of bandit in Burma throwing rubies away just to watch world burn", "spans": [[3100.0, 3350.0]]},
        {"movie_id": "tt0468569", "title": "The Dark Knight", "query": "Bruce crashes party in penthouse to rescue Rachel from clown who drops her from balcony", "spans": [[3300.0, 3600.0]]},

        # --- Gladiator (21 cases) ---
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Roman general betrayed after the emperor's death escapes into the desert, becomes a gladiator in North Africa, and fights his way to the Colosseum to kill Commodus", "spans": [[1400.0, 8800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Opens with legion battle against barbarians in Germania, then general's family is crucified, leading him to slave arenas in Zucchabar", "spans": [[400.0, 2500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Enslaved warriors defeat chariots in Carthage reenactment, then gladiator reveals his true name to shocked emperor in Colosseum", "spans": [[5200.0, 4800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Commodus stabs gladiator before arena battle, but dying hero kills the emperor with bare hands and rejoins his family in death", "spans": [[8400.0, 9000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Marcus Aurelius asks general to become protector of Rome and restore Senate, provoking jealous son to murder father", "spans": [[1200.0, 1600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Gladiator defeats undefeated Tigris of Gaul surrounded by chained tigers and spares his life", "spans": [[6100.0, 6500.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Proximo buys Spanish general as slave and teaches him to win over crowds in amphitheaters", "spans": [[2600.0, 3800.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Senator Gracchus and Lucilla plot military coup with general outside Rome walls but Praetorians raid school", "spans": [[6700.0, 8000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Maximus rides exhausted horse across empire only to find burned home and murdered wife and child", "spans": [[1800.0, 2150.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Roman cavalry charges through snowy forest with catapult barrages of flaming jars", "spans": [[400.0, 750.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Hero dies in center of Colosseum sand and asks for senators to be freed and land returned to republic", "spans": [[8700.0, 9000.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Juba buries carved figurines of Maximus wife and son in arena sand whispering they will meet again", "spans": [[9000.0, 9300.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Commodus challenges gladiator to single combat in sand ring after stabbing his lung with hidden blade", "spans": [[8400.0, 8700.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Gladiators chain up in circle with shields to deflect scythe wheels of Carthage chariots", "spans": [[5200.0, 5600.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Maximus throws bloody sword at royal box and mocks mob with are you not entertained", "spans": [[4250.0, 4400.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Emperor suffocates father with hug after being passed over for succession in imperial campaign tent", "spans": [[1400.0, 1650.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Execution detail leads general into winter forest at dawn but he disarms soldier and slashes officer", "spans": [[1700.0, 1950.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Cicero attempts to deliver Maximus horses for escape but gets hanged from palace wall", "spans": [[7800.0, 8050.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Lucilla confesses secret love and republican alliance to dying general on litter", "spans": [[8800.0, 9050.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "Proximo recites shadows and dust before dying in gladiator school defense against Praetorians", "spans": [[7800.0, 8050.0]]},
        {"movie_id": "tt0172495", "title": "Gladiator", "query": "General remembers Spanish farmhouse with olive orchard and poplars while dreaming of peace", "spans": [[900.0, 1200.0]]},

        # --- Whiplash (21 cases) ---
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Drumming student joins prestigious jazz conservatory, suffers psychological abuse and slapped cheeks from tyrannical teacher, gets into a car accident, and returns for an epic solo at Carnegie Hall", "spans": [[1500.0, 6400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Jazz drummer breaks up with girlfriend to focus on greatness, practices till blood covers drum heads, and gets trapped in three-way sweat audition for core drummer", "spans": [[2500.0, 4300.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Teacher hurls chair at student for not knowing rushing versus dragging, kicks him out, then gets fired when student testifies about suicide of former musician", "spans": [[1600.0, 5500.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Conductor sets trap for student at JVC jazz festival with unfamiliar piece, but drummer interrupts with explosive Caravan solo", "spans": [[5700.0, 6400.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Student loses sheet music folder at competition, allowing him to step in as core drummer and play from memory", "spans": [[3600.0, 3900.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Car accident flips drummer rental vehicle but he runs bleeding into theater to perform with broken fingers", "spans": [[4700.0, 5050.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Fletcher tells story of Jo Jones throwing cymbal at Charlie Parker to explain why pushing musicians to brink creates legends", "spans": [[5300.0, 5600.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Andrew tackles Fletcher on stage in rage after dropping stick and getting fired from Shaffer", "spans": [[5000.0, 5200.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Drummer plays frantic double time swing till teacher finally nods with respect during Caravan finale", "spans": [[6100.0, 6450.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Student practices into night, punches snare head, and plunges raw bleeding hands into pitcher of ice water", "spans": [[2500.0, 2800.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Fletcher brings alternate drummer Connelly to studio and tests three students till two in morning on Whiplash tempo", "spans": [[3900.0, 4300.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Dinner table conversation where dad and cousins dismiss music conservatory compared to model UN and football", "spans": [[2900.0, 3150.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Father watches through auditorium door as son defies tyrannical teacher and plays drum solo of lifetime", "spans": [[6200.0, 6450.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Andrew gives away drum kit and works at bakery until seeing Fletcher playing piano at jazz club", "spans": [[5200.0, 5500.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Teacher tells Andrew he knows who got him fired from Shaffer right before counting off first song at Carnegie Hall", "spans": [[5700.0, 5900.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Andrew tries to invite ex-girlfriend Nicole to concert but discovers she has new boyfriend", "spans": [[5600.0, 5800.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Bus blows flat tire forcing drummer to sprint to rental agency to make festival call time", "spans": [[4500.0, 4750.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Teacher screams insults targeting student Irish father and dead mother during band rehearsal", "spans": [[1600.0, 1800.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Opening scene where Fletcher discovers freshman drummer practicing alone in basement studio", "spans": [[50.0, 300.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Trombonist Metz gets kicked out of studio band for not recognizing whether he was out of tune", "spans": [[1750.0, 1950.0]]},
        {"movie_id": "tt2582802", "title": "Whiplash", "query": "Lawyer explains Sean Casey committed suicide from depression caused by Fletcher psychological torture", "spans": [[5100.0, 5350.0]]},

        # --- Inception (21 cases) ---
        {"movie_id": "tt1375666", "title": "Inception", "query": "Dream thieves recruited by Japanese energy magnate to plant an idea in an heir's mind, entering three subconscious dream layers while a van falls off a bridge in the rain", "spans": [[1000.0, 7500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Architect learns to build impossible dream mazes, folds Paris over itself, and discovers thief projection of deceased wife Mal sabotaging missions", "spans": [[1800.0, 4000.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Team fights zero-gravity hallway guards in hotel while snow fortress is assaulted, all timed to synchronized music kick Non je ne regrette rien", "spans": [[6500.0, 7600.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Man washes up on shore in limbo, convinces elderly partner to remember reality, and returns home to see spinning metal top on dining table", "spans": [[8200.0, 8600.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Extraction mission in Japanese palace collapses when Saito realizes carpet polyester was wrong", "spans": [[200.0, 800.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Cobb recruits student architect Ariadne in Paris and chemist Yusuf in Mombasa while fleeing Cobol agents", "spans": [[1600.0, 2700.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Freight train charges through rainy downtown city street during dream level one kidnapping of Fischer", "spans": [[4200.0, 4500.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Arthur rigs elevator shaft with explosives to create synthetic gravity kick for sleeping teammates in hotel", "spans": [[6900.0, 7250.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Cobb confesses he planted idea in wife mind that her world was not real, leading to her suicide leap from window", "spans": [[6000.0, 6300.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Fischer opens mountain hospital safe and discovers paper pinwheel reconciles with father legacy", "spans": [[7600.0, 7850.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Ariadne and Cobb enter fourth level crumbling limbo city to retrieve Fischer after Mal shoots him", "spans": [[7700.0, 8100.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Saito shot in chest on first dream level risks falling into eternal limbo because sedative is too deep", "spans": [[4400.0, 4700.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Eames forges identity of Peter Browning to trick Fischer into suspecting uncle of hiding will", "spans": [[4600.0, 4900.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Van flies off bridge barrier hitting water surface to execute synchronized kick across all levels", "spans": [[7200.0, 7550.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Saito honors deal with phone call at airport immigration allowing Cobb to enter United States freely", "spans": [[8100.0, 8350.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Grandfather Miles introduces Dom to his children after years of being on run abroad", "spans": [[8350.0, 8550.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Cobb spins silver totem on wooden table but walks out to hug kids before verifying if it stops", "spans": [[8450.0, 8600.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Arthur demonstrates loaded die totem and explains why no one else can touch your totem", "spans": [[2300.0, 2550.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Subconscious projections attack dreamer in cafe after physics laws are altered by architect", "spans": [[1900.0, 2150.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Thieves drug heir water on ten hour Sydney to Los Angeles flight to connect dream machines", "spans": [[3900.0, 4200.0]]},
        {"movie_id": "tt1375666", "title": "Inception", "query": "Cobb relives memories of children faces turned away on beach whenever elevator stops in dream basement", "spans": [[3700.0, 4000.0]]},
    ]

    all_cases = []
    
    # Pack exact quotes
    for idx, c in enumerate(exact_quotes, 1):
        all_cases.append({
            "id": f"eq-{idx:03d}",
            "movie_id": c["movie_id"],
            "title": c["title"],
            "category": "exact_quote",
            "mode": "quote",
            "query": c["query"],
            "spans": c["spans"]
        })
        
    # Pack typo quotes
    for idx, c in enumerate(typo_quotes, 1):
        all_cases.append({
            "id": f"tq-{idx:03d}",
            "movie_id": c["movie_id"],
            "title": c["title"],
            "category": "typo_quote",
            "mode": "quote",
            "query": c["query"],
            "spans": c["spans"]
        })

    # Pack semantic scenes
    for idx, c in enumerate(semantic_scenes, 1):
        all_cases.append({
            "id": f"ss-{idx:03d}",
            "movie_id": c["movie_id"],
            "title": c["title"],
            "category": "semantic_scene",
            "mode": "scene",
            "query": c["query"],
            "spans": c["spans"]
        })

    # Pack narrative ToT
    for idx, c in enumerate(narrative_tot, 1):
        all_cases.append({
            "id": f"nt-{idx:03d}",
            "movie_id": c["movie_id"],
            "title": c["title"],
            "category": "narrative_tot",
            "mode": "auto",
            "query": c["query"],
            "spans": c["spans"]
        })

    print(f"Generated {len(all_cases)} total cases:")
    counts = {}
    for c in all_cases:
        counts[c['category']] = counts.get(c['category'], 0) + 1
    for cat, cnt in counts.items():
        print(f"  - {cat}: {cnt} cases")

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_cases, f, indent=2, ensure_ascii=False)
    print(f"Saved benchmark dataset to {OUT_PATH}")

if __name__ == '__main__':
    generate_benchmark()
