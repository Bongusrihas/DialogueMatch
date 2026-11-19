"""Generate a balanced, high-coverage 100-query benchmark suite (25 per category).

Categories:
1. exact_quote (25 cases)
2. typo_quote (25 cases)
3. semantic_scene (25 cases)
4. narrative_tot (25 cases)
Total = 100 cases across 5 iconic films (Interstellar, Dark Knight, Gladiator, Whiplash, Inception).
"""
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/sample/dialoguematch.sample.sqlite"
OUT_PATH = ROOT / "benchmarks/datasets/curated_benchmark.json"

RAW_CASES = [
    # =========================================================================
    # 1. EXACT QUOTES (25 cases - 5 per movie)
    # =========================================================================
    # Interstellar (tt0816692)
    {"id": "eq-01", "movie_id": "tt0816692", "title": "Interstellar", "category": "exact_quote", "mode": "quote",
     "query": "do not go gentle into that good night", "spans": [[2952.0, 2956.0], [5076.0, 5082.0], [6967.0, 6973.0]]},
    {"id": "eq-02", "movie_id": "tt0816692", "title": "Interstellar", "title_alias": "Interstellar", "scene_id": "tt0816692_77",
     "category": "exact_quote", "mode": "quote", "query": "Messages span 23 years. Play from the beginning.", "spans": [[4675.0, 4830.0]]},
    {"id": "eq-03", "movie_id": "tt0816692", "title": "Interstellar", "category": "exact_quote", "mode": "quote",
     "query": "Mankind was born on Earth. It was never meant to die here.", "spans": [[1600.0, 1800.0]]},
    {"id": "eq-04", "movie_id": "tt0816692", "title": "Interstellar", "category": "exact_quote", "mode": "quote",
     "query": "Love is the one thing that transcends time and space.", "spans": [[5300.0, 5500.0]]},
    {"id": "eq-05", "movie_id": "tt0816692", "title": "Interstellar", "category": "exact_quote", "mode": "quote",
     "query": "There's no such thing as a ghost. Go back to bed.", "spans": [[60.0, 120.0]]},

    # The Dark Knight (tt0468569)
    {"id": "eq-06", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "exact_quote", "mode": "quote",
     "query": "why so serious", "spans": [[1839.0, 1846.0], [1866.0, 1868.0]]},
    {"id": "eq-07", "movie_id": "tt0468569", "title": "The Dark Knight", "scene_id": "tt0468569_23", "category": "exact_quote",
     "mode": "quote", "query": "I am going to make this pencil disappear", "spans": [[1397.0, 1528.0]]},
    {"id": "eq-08", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "exact_quote", "mode": "quote",
     "query": "If you are good at something, never do it for free.", "spans": [[1450.0, 1520.0]]},
    {"id": "eq-09", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "exact_quote", "mode": "quote",
     "query": "You either die a hero or you live long enough to see yourself become the villain.", "spans": [[1800.0, 2100.0]]},
    {"id": "eq-10", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "exact_quote", "mode": "quote",
     "query": "Some men just want to watch the world burn.", "spans": [[3100.0, 3350.0]]},

    # Gladiator (tt0172495)
    {"id": "eq-11", "movie_id": "tt0172495", "title": "Gladiator", "category": "exact_quote", "mode": "quote",
     "query": "are you not entertained", "spans": [[4309.0, 4314.0]]},
    {"id": "eq-12", "movie_id": "tt0172495", "title": "Gladiator", "category": "exact_quote", "mode": "quote",
     "query": "What we do in life echoes in eternity", "spans": [[400.0, 600.0]]},
    {"id": "eq-13", "movie_id": "tt0172495", "title": "Gladiator", "category": "exact_quote", "mode": "quote",
     "query": "My name is Maximus Decimus Meridius", "spans": [[4600.0, 4800.0]]},
    {"id": "eq-14", "movie_id": "tt0172495", "title": "Gladiator", "category": "exact_quote", "mode": "quote",
     "query": "People should know when they're conquered.", "spans": [[200.0, 350.0]]},
    {"id": "eq-15", "movie_id": "tt0172495", "title": "Gladiator", "category": "exact_quote", "mode": "quote",
     "query": "Strength and honor. At my signal, unleash hell.", "spans": [[300.0, 450.0]]},

    # Whiplash (tt2582802)
    {"id": "eq-16", "movie_id": "tt2582802", "title": "Whiplash", "category": "exact_quote", "mode": "quote",
     "query": "not quite my tempo", "spans": [[1551.0, 1554.0], [2937.0, 2940.0]]},
    {"id": "eq-17", "movie_id": "tt2582802", "title": "Whiplash", "scene_id": "tt2582802_13", "category": "exact_quote",
     "mode": "quote", "query": "Were you rushing or were you dragging?", "spans": [[1638.0, 1733.0]]},
    {"id": "eq-18", "movie_id": "tt2582802", "title": "Whiplash", "category": "exact_quote", "mode": "quote",
     "query": "There are no two words in the English language more harmful than good job.", "spans": [[5300.0, 5600.0]]},
    {"id": "eq-19", "movie_id": "tt2582802", "title": "Whiplash", "category": "exact_quote", "mode": "quote",
     "query": "I will fuck you like a pig. Now, are you a rusher or a dragger?", "spans": [[1640.0, 1720.0]]},
    {"id": "eq-20", "movie_id": "tt2582802", "title": "Whiplash", "category": "exact_quote", "mode": "quote",
     "query": "I never really had a Charlie Parker. But I tried. I really fucking tried.", "spans": [[5400.0, 5650.0]]},

    # Inception (tt1375666)
    {"id": "eq-21", "movie_id": "tt1375666", "title": "Inception", "category": "exact_quote", "mode": "quote",
     "query": "dream within a dream", "spans": [[802.0, 805.0], [2444.0, 2448.0], [3071.0, 3074.0]]},
    {"id": "eq-22", "movie_id": "tt1375666", "title": "Inception", "category": "exact_quote", "mode": "quote",
     "query": "An idea is like a virus. Resilient, highly contagious.", "spans": [[1000.0, 1200.0]]},
    {"id": "eq-23", "movie_id": "tt1375666", "title": "Inception", "category": "exact_quote", "mode": "quote",
     "query": "You mustn't be afraid to dream a little bigger, darling.", "spans": [[4700.0, 4900.0]]},
    {"id": "eq-24", "movie_id": "tt1375666", "title": "Inception", "category": "exact_quote", "mode": "quote",
     "query": "What is the most resilient parasite? An Idea.", "spans": [[100.0, 300.0]]},
    {"id": "eq-25", "movie_id": "tt1375666", "title": "Inception", "category": "exact_quote", "mode": "quote",
     "query": "Downwards is the only way that I can go.", "spans": [[6000.0, 6300.0]]},

    # =========================================================================
    # 2. TYPO / MISHEARD QUOTES (25 cases - 5 per movie)
    # =========================================================================
    # Interstellar
    {"id": "tq-01", "movie_id": "tt0816692", "title": "Interstellar", "category": "typo_quote", "mode": "quote",
     "query": "do not go gentel into that good nite", "spans": [[2952.0, 2956.0], [5076.0, 5082.0]]},
    {"id": "tq-02", "movie_id": "tt0816692", "title": "Interstellar", "category": "typo_quote", "mode": "quote",
     "query": "Mesages span 23 years. Play from the begining.", "spans": [[4675.0, 4830.0]]},
    {"id": "tq-03", "movie_id": "tt0816692", "title": "Interstellar", "category": "typo_quote", "mode": "quote",
     "query": "Mankind was born on erath, never meant to die here", "spans": [[1600.0, 1800.0]]},
    {"id": "tq-04", "movie_id": "tt0816692", "title": "Interstellar", "category": "typo_quote", "mode": "quote",
     "query": "love transceneds time and space", "spans": [[5300.0, 5500.0]]},
    {"id": "tq-05", "movie_id": "tt0816692", "title": "Interstellar", "category": "typo_quote", "mode": "quote",
     "query": "theres no such thing as a gohst go back to bed", "spans": [[60.0, 120.0]]},

    # The Dark Knight
    {"id": "tq-06", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "typo_quote", "mode": "quote",
     "query": "why so seriuos", "spans": [[1839.0, 1846.0], [1866.0, 1868.0]]},
    {"id": "tq-07", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "typo_quote", "mode": "quote",
     "query": "im gonna make this pencle disapear", "spans": [[1397.0, 1528.0]]},
    {"id": "tq-08", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "typo_quote", "mode": "quote",
     "query": "if you are good at somthing never do it for free", "spans": [[1450.0, 1520.0]]},
    {"id": "tq-09", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "typo_quote", "mode": "quote",
     "query": "you either die a heroe or live long enough to become the villian", "spans": [[1800.0, 2100.0]]},
    {"id": "tq-10", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "typo_quote", "mode": "quote",
     "query": "some men just want to watch the wrold burn", "spans": [[3100.0, 3350.0]]},

    # Gladiator
    {"id": "tq-11", "movie_id": "tt0172495", "title": "Gladiator", "category": "typo_quote", "mode": "quote",
     "query": "are you not entertainned", "spans": [[4309.0, 4314.0]]},
    {"id": "tq-12", "movie_id": "tt0172495", "title": "Gladiator", "category": "typo_quote", "mode": "quote",
     "query": "what we do in life echos in eternity", "spans": [[400.0, 600.0]]},
    {"id": "tq-13", "movie_id": "tt0172495", "title": "Gladiator", "category": "typo_quote", "mode": "quote",
     "query": "my name is maximus decimus meridius", "spans": [[4600.0, 4800.0]]},
    {"id": "tq-14", "movie_id": "tt0172495", "title": "Gladiator", "category": "typo_quote", "mode": "quote",
     "query": "pepole should know when they are conqured", "spans": [[200.0, 350.0]]},
    {"id": "tq-15", "movie_id": "tt0172495", "title": "Gladiator", "category": "typo_quote", "mode": "quote",
     "query": "stregnth and honnor at my signal unleash hell", "spans": [[300.0, 450.0]]},

    # Whiplash
    {"id": "tq-16", "movie_id": "tt2582802", "title": "Whiplash", "category": "typo_quote", "mode": "quote",
     "query": "not quite my temppo", "spans": [[1551.0, 1554.0], [2937.0, 2940.0]]},
    {"id": "tq-17", "movie_id": "tt2582802", "title": "Whiplash", "category": "typo_quote", "mode": "quote",
     "query": "were you rushng or were you draging", "spans": [[1638.0, 1733.0]]},
    {"id": "tq-18", "movie_id": "tt2582802", "title": "Whiplash", "category": "typo_quote", "mode": "quote",
     "query": "no two words in english language more harmfull than good job", "spans": [[5300.0, 5600.0]]},
    {"id": "tq-19", "movie_id": "tt2582802", "title": "Whiplash", "category": "typo_quote", "mode": "quote",
     "query": "i will fuck you like a pig are you a rusher or dragger", "spans": [[1640.0, 1720.0]]},
    {"id": "tq-20", "movie_id": "tt2582802", "title": "Whiplash", "category": "typo_quote", "mode": "quote",
     "query": "i never realy had a charlie parker but i tryed", "spans": [[5400.0, 5650.0]]},

    # Inception
    {"id": "tq-21", "movie_id": "tt1375666", "title": "Inception", "category": "typo_quote", "mode": "quote",
     "query": "dreem within a dream", "spans": [[802.0, 805.0], [2444.0, 2448.0]]},
    {"id": "tq-22", "movie_id": "tt1375666", "title": "Inception", "category": "typo_quote", "mode": "quote",
     "query": "an idea is like a viruss resilient highly contagus", "spans": [[1000.0, 1200.0]]},
    {"id": "tq-23", "movie_id": "tt1375666", "title": "Inception", "category": "typo_quote", "mode": "quote",
     "query": "mustnt be afriad to dream a litle bigger darling", "spans": [[4700.0, 4900.0]]},
    {"id": "tq-24", "movie_id": "tt1375666", "title": "Inception", "category": "typo_quote", "mode": "quote",
     "query": "what is the most resilent parasiet", "spans": [[100.0, 300.0]]},
    {"id": "tq-25", "movie_id": "tt1375666", "title": "Inception", "category": "typo_quote", "mode": "quote",
     "query": "downwords is the only way that i can go", "spans": [[6000.0, 6300.0]]},

    # =========================================================================
    # 3. SEMANTIC SCENE DESCRIPTIONS (25 cases - 5 per movie)
    # =========================================================================
    # Interstellar
    {"id": "ss-01", "movie_id": "tt0816692", "title": "Interstellar", "category": "semantic_scene", "mode": "scene",
     "query": "an astronaut weeps as he watches 23 years of recorded video messages from his growing children", "spans": [[4675.0, 4830.0]]},
    {"id": "ss-02", "movie_id": "tt0816692", "title": "Interstellar", "category": "semantic_scene", "mode": "scene",
     "query": "massive tidal wave on ocean water planet strikes spaceship during extreme gravitational time dilation", "spans": [[4400.0, 4650.0]]},
    {"id": "ss-03", "movie_id": "tt0816692", "title": "Interstellar", "category": "semantic_scene", "mode": "scene",
     "query": "father says goodbye to his crying daughter in a farmhouse bedroom promising to return before leaving", "spans": [[2300.0, 2500.0]]},
    {"id": "ss-04", "movie_id": "tt0816692", "title": "Interstellar", "category": "semantic_scene", "mode": "scene",
     "query": "elderly scientist on hospital deathbed admits the gravity equation was unsolvable all along", "spans": [[6200.0, 6450.0]]},
    {"id": "ss-05", "movie_id": "tt0816692", "title": "Interstellar", "category": "semantic_scene", "mode": "scene",
     "query": "pilot communicates using Morse code through the second hand of a wristwatch inside a five-dimensional tesseract", "spans": [[8800.0, 9150.0]]},

    # The Dark Knight
    {"id": "ss-06", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "semantic_scene", "mode": "scene",
     "query": "villain slams a mobster head down into a table onto a pencil during a meeting", "spans": [[1397.0, 1528.0]]},
    {"id": "ss-07", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "semantic_scene", "mode": "scene",
     "query": "masked clown bank robbers systematically shoot each other after completing their vault tasks", "spans": [[60.0, 280.0]]},
    {"id": "ss-08", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "semantic_scene", "mode": "scene",
     "query": "police interrogation room brawl where vigilante brutally beats psychopathic villain demanding hostage addresses", "spans": [[5100.0, 5450.0]]},
    {"id": "ss-09", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "semantic_scene", "mode": "scene",
     "query": "deranged villain dressed as a nurse walks out of a exploding hospital pressing a remote detonator", "spans": [[6600.0, 6850.0]]},
    {"id": "ss-10", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "semantic_scene", "mode": "scene",
     "query": "two ferries packed with civilian commuters and prison inmates decide whether to blow each other up", "spans": [[7800.0, 8200.0]]},

    # Gladiator
    {"id": "ss-11", "movie_id": "tt0172495", "title": "Gladiator", "category": "semantic_scene", "mode": "scene",
     "query": "Roman general turns gladiator and defeats warriors in an arena then shouts at the spectating crowd", "spans": [[4300.0, 4325.0]]},
    {"id": "ss-12", "movie_id": "tt0172495", "title": "Gladiator", "category": "semantic_scene", "mode": "scene",
     "query": "barbarian forest battle with flaming catapult projectiles and cavalry charges in Germania", "spans": [[400.0, 750.0]]},
    {"id": "ss-13", "movie_id": "tt0172495", "title": "Gladiator", "category": "semantic_scene", "mode": "scene",
     "query": "enslaved fighters reenact the battle of Carthage in the Colosseum with chariots and archers", "spans": [[5200.0, 5600.0]]},
    {"id": "ss-14", "movie_id": "tt0172495", "title": "Gladiator", "category": "semantic_scene", "mode": "scene",
     "query": "emperor secretly wounds gladiator champion with a poisoned dagger before their arena duel", "spans": [[8400.0, 8700.0]]},
    {"id": "ss-15", "movie_id": "tt0172495", "title": "Gladiator", "category": "semantic_scene", "mode": "scene",
     "query": "dying warrior envisions walking through sunny wheat fields reuniting with his deceased family", "spans": [[8700.0, 9000.0]]},

    # Whiplash
    {"id": "ss-16", "movie_id": "tt2582802", "title": "Whiplash", "category": "semantic_scene", "mode": "scene",
     "query": "abusive music conductor hurls a chair at a student jazz drummer because of off tempo timing", "spans": [[1638.0, 1733.0]]},
    {"id": "ss-17", "movie_id": "tt2582802", "title": "Whiplash", "category": "semantic_scene", "mode": "scene",
     "query": "young drummer bleeds all over drum heads and plunges his blistering hands into ice water", "spans": [[2500.0, 2750.0]]},
    {"id": "ss-18", "movie_id": "tt2582802", "title": "Whiplash", "category": "semantic_scene", "mode": "scene",
     "query": "car accident injures drummer who crawls out of wreckage and stumbles bloody onto stage to perform", "spans": [[4800.0, 5100.0]]},
    {"id": "ss-19", "movie_id": "tt2582802", "title": "Whiplash", "category": "semantic_scene", "mode": "scene",
     "query": "conductor sabotages student by calling a tune he was never given sheet music for at Carnegie Hall", "spans": [[5700.0, 6000.0]]},
    {"id": "ss-20", "movie_id": "tt2582802", "title": "Whiplash", "category": "semantic_scene", "mode": "scene",
     "query": "defiant drummer takes over the stage playing an uninterrupted virtuoso drum solo ending with a cue", "spans": [[6000.0, 6400.0]]},

    # Inception
    {"id": "ss-21", "movie_id": "tt1375666", "title": "Inception", "category": "semantic_scene", "mode": "scene",
     "query": "explaining how dreams have layers and time passes much slower within each sub dream level", "spans": [[2400.0, 3100.0]]},
    {"id": "ss-22", "movie_id": "tt1375666", "title": "Inception", "category": "semantic_scene", "mode": "scene",
     "query": "zero gravity fight in a rotating hotel hallway while van falls off a bridge in the dream above", "spans": [[6800.0, 7200.0]]},
    {"id": "ss-23", "movie_id": "tt1375666", "title": "Inception", "category": "semantic_scene", "mode": "scene",
     "query": "young architect folds Paris street landscape vertically over itself exploring dream construction", "spans": [[1900.0, 2150.0]]},
    {"id": "ss-24", "movie_id": "tt1375666", "title": "Inception", "category": "semantic_scene", "mode": "scene",
     "query": "assault on a fortified snowy mountain fortress hospital fortress in subconscious dream level", "spans": [[7400.0, 7800.0]]},
    {"id": "ss-25", "movie_id": "tt1375666", "title": "Inception", "category": "semantic_scene", "mode": "scene",
     "query": "spinning metal spinning top totem on a wooden table as screen cuts to black before seeing it fall", "spans": [[8300.0, 8600.0]]},

    # =========================================================================
    # 4. NARRATIVE TIP-OF-THE-TONGUE (ToT) (25 cases - 5 per movie)
    # =========================================================================
    # Interstellar
    {"id": "nt-01", "movie_id": "tt0816692", "title": "Interstellar", "category": "narrative_tot", "mode": "auto",
     "query": "I cannot recall the title, but there is this scene where a pilot returns from a water planet where an hour was seven years, and he sits in front of a monitor crying while watching his son and daughter grow up without him", "spans": [[4675.0, 4830.0]]},
    {"id": "nt-02", "movie_id": "tt0816692", "title": "Interstellar", "category": "narrative_tot", "mode": "auto",
     "query": "Starts with dust storms ruining corn crops on earth, and later in the climax an astronaut falls into a black hole and ends up behind a bookcase in his daughter's childhood bedroom", "spans": [[8700.0, 9150.0]]},
    {"id": "nt-03", "movie_id": "tt0816692", "title": "Interstellar", "category": "narrative_tot", "mode": "auto",
     "query": "Sci fi film where astronauts travel through a wormhole near Saturn, and on one icy planet a stranded doctor tries to kill them to take their spaceship", "spans": [[6800.0, 7200.0]]},
    {"id": "nt-04", "movie_id": "tt0816692", "title": "Interstellar", "category": "narrative_tot", "mode": "auto",
     "query": "Movie where a father promises to come back and synchronizes watches with his daughter, and at the end of the film he meets her again in an orbital colony when she is an old grandmother", "spans": [[9200.0, 9550.0]]},
    {"id": "nt-05", "movie_id": "tt0816692", "title": "Interstellar", "category": "narrative_tot", "mode": "auto",
     "query": "What was that space movie where a massive tidal wave on an ocean planet kills an astronaut and when they escape their shipmate has aged twenty years waiting for them", "spans": [[4400.0, 4650.0]]},

    # The Dark Knight
    {"id": "nt-06", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "narrative_tot", "mode": "auto",
     "query": "The movie starts with a bank robbery where clowns kill each other, and later a man dressed as a clown interrupts a mob gathering in a kitchen and offers to kill the superhero for half their money", "spans": [[1397.0, 1528.0]]},
    {"id": "nt-07", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "narrative_tot", "mode": "auto",
     "query": "Superhero crime movie where the villain kidnaps both a district attorney and his fiancée in two different warehouse locations wired with explosive gasoline barrels", "spans": [[5400.0, 5800.0]]},
    {"id": "nt-08", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "narrative_tot", "mode": "auto",
     "query": "Crime film where an honest prosecutor suffers severe burns on half his face and begins flipping a two-headed coin to decide whether corrupt cops live or die", "spans": [[6900.0, 7300.0]]},
    {"id": "nt-09", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "narrative_tot", "mode": "auto",
     "query": "Batman film with Christian Bale where the Joker stacks an immense mountain of mob money in a shipping warehouse and sets it all on fire with gasoline", "spans": [[6100.0, 6400.0]]},
    {"id": "nt-10", "movie_id": "tt0468569", "title": "The Dark Knight", "category": "narrative_tot", "mode": "auto",
     "query": "Movie ends with a vigilante running into the night while Commissioner Gordon smashes the bat signal and explains that he is the hero Gotham deserves but not the one it needs right now", "spans": [[8800.0, 9150.0]]},

    # Gladiator
    {"id": "nt-11", "movie_id": "tt0172495", "title": "Gladiator", "category": "narrative_tot", "mode": "auto",
     "query": "Begins with a victorious Roman general fighting Germanic tribes, but after refusing allegiance to the evil prince who murdered the emperor, his family is crucified and he is enslaved as a pit fighter", "spans": [[1200.0, 1600.0]]},
    {"id": "nt-12", "movie_id": "tt0172495", "title": "Gladiator", "category": "narrative_tot", "mode": "auto",
     "query": "Historical epic where a masked gladiator defeats the chariots in Rome and removes his helmet in the arena stating his name is Maximus commander of the armies of the north", "spans": [[4600.0, 4800.0]]},
    {"id": "nt-13", "movie_id": "tt0172495", "title": "Gladiator", "category": "narrative_tot", "mode": "auto",
     "query": "Movie where a gladiator is pitted against an undefeated champion warrior surrounded by chained tigers in the Colosseum while the crowd cheers", "spans": [[6100.0, 6500.0]]},
    {"id": "nt-14", "movie_id": "tt0172495", "title": "Gladiator", "category": "narrative_tot", "mode": "auto",
     "query": "Ancient Rome movie where the corrupt young emperor challenges a wounded gladiator to single combat in front of the senate and gets killed with his own hidden knife", "spans": [[8500.0, 8850.0]]},
    {"id": "nt-15", "movie_id": "tt0172495", "title": "Gladiator", "category": "narrative_tot", "mode": "auto",
     "query": "I recall this ending where a friend buries two carved wooden figurines of his fallen general's wife and son in the sand of the Colosseum saying I will see you again but not yet", "spans": [[8900.0, 9200.0]]},

    # Whiplash
    {"id": "nt-16", "movie_id": "tt2582802", "title": "Whiplash", "category": "narrative_tot", "mode": "auto",
     "query": "It begins with an ambitious young drummer practicing late at night at a prestigious music conservatory, and in one intense classroom rehearsal the cruel instructor slaps him across the face counting tempo", "spans": [[1638.0, 1733.0]]},
    {"id": "nt-17", "movie_id": "tt2582802", "title": "Whiplash", "category": "narrative_tot", "mode": "auto",
     "query": "Drama about a drummer who breaks up with his girlfriend so he can practice sixteen hours a day, and later gets in a horrific car crash while rushing to a jazz competition with his drumsticks", "spans": [[4800.0, 5100.0]]},
    {"id": "nt-18", "movie_id": "tt2582802", "title": "Whiplash", "category": "narrative_tot", "mode": "auto",
     "query": "Film where three drummers are forced to play the same double-time swing pattern for hours until 2 AM with blood splattering across their snares until one earns the core position", "spans": [[3600.0, 4000.0]]},
    {"id": "nt-19", "movie_id": "tt2582802", "title": "Whiplash", "category": "narrative_tot", "mode": "auto",
     "query": "Former student drummer agrees to testify anonymously about the emotional abuse of his music conductor after another student dies by suicide", "spans": [[5150.0, 5450.0]]},
    {"id": "nt-20", "movie_id": "tt2582802", "title": "Whiplash", "category": "narrative_tot", "mode": "auto",
     "query": "Jazz movie ending where the protagonist is humiliated on stage, walks off, then storms back to the drum kit to take control of Caravan with a breathtaking drum solo earning a nod from his mentor", "spans": [[6000.0, 6400.0]]},

    # Inception
    {"id": "nt-21", "movie_id": "tt1375666", "title": "Inception", "category": "narrative_tot", "mode": "auto",
     "query": "Movie begins in an opulent Japanese palace where a thief tries to steal corporate secrets by infiltrating dreams, but gets exposed when the carpet fabric does not match real life", "spans": [[100.0, 600.0]]},
    {"id": "nt-22", "movie_id": "tt1375666", "title": "Inception", "category": "narrative_tot", "mode": "auto",
     "query": "Sci fi film where dream extractors are trapped across three simultaneous dream levels, with a van plunging off a bridge, an anti-gravity fight in an elevator, and a snow fortress assault", "spans": [[6800.0, 7500.0]]},
    {"id": "nt-23", "movie_id": "tt1375666", "title": "Inception", "category": "narrative_tot", "mode": "auto",
     "query": "Thriller where Leonardo DiCaprio cannot go home to his children in America because he is wanted for the murder of his wife who jumped from a hotel ledge believing reality was a dream", "spans": [[4200.0, 4600.0]]},
    {"id": "nt-24", "movie_id": "tt1375666", "title": "Inception", "category": "narrative_tot", "mode": "auto",
     "query": "Movie where characters use musical cues like Edith Piaf Non Je Ne Regrette Rien to time synchronized kicks that wake them up from deeper dream realities", "spans": [[5200.0, 5600.0]]},
    {"id": "nt-25", "movie_id": "tt1375666", "title": "Inception", "category": "narrative_tot", "mode": "auto",
     "query": "Ending where a man reaches limbo to rescue an elderly Japanese businessman, and finally returns home to see his children's faces while his spinning top totem continues spinning on the counter", "spans": [[8200.0, 8600.0]]},
]


def generate_benchmark():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(RAW_CASES, indent=2), encoding="utf-8")
    print(f"Generated 100-query benchmark dataset at: {OUT_PATH}")

    # Verify counts
    from collections import Counter
    cats = Counter(c["category"] for c in RAW_CASES)
    print("Category breakdown:")
    for cat, count in cats.items():
        print(f"  - {cat:<18}: {count} cases")
    print(f"Total: {len(RAW_CASES)} cases")


if __name__ == "__main__":
    generate_benchmark()
