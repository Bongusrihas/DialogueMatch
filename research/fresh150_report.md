# Fresh 150-query audit

Completed: 150/150. Query set SHA-256: `9c905bc65ab404fec3b0922c147a27dc9fd7d3ea07f339e8a133f2499d01f1e8`.

The query set was fixed before running. No search changes were made during this run. These are newly authored development probes across 40 movies excluded from the older 310-query evaluation. They are not independently collected human requests. The first 120 queries are three variants of 40 scene seeds, so they are correlated rather than 120 independent events. The 30 visual queries have manually supplied movie labels, no verified time labels, and are excluded from scene metrics. Natural descriptions were written using local subtitle text and generated summaries; summaries can be wrong. Timing labels follow local subtitles and have not been checked against movie video.

| Category | Queries | Movie @1 / @5 / @10 | Scene @1 / @5 / @10 | Median seconds |
|---|---:|---|---|---:|
| direct_dialogue | 40 | 40 / 40 / 40 | 40 / 40 / 40 | 0.10 |
| imperfect_dialogue | 40 | 40 / 40 / 40 | 40 / 40 / 40 | 3.35 |
| natural_description | 20 | 14 / 17 / 17 | 12 / 15 / 15 | 21.32 |
| long_natural_description | 20 | 1 / 4 / 7 | 0 / 2 / 3 | 29.86 |
| visual_memory | 30 | 10 / 15 / 16 | No span labels | 29.23 |

For the 40 description probes, the labeled passage ID entered the candidate pool in 35 cases and reached reranking in 34. Accepted span Hit@5 was 17. In 4 cases the expected movie appeared in the first five but its labeled span did not. Retrieval, shortlist selection, and ranking therefore have separate measurable failure modes.

Search received only each query and its mode: expected movie IDs and scene labels were used only for scoring, with no movie filter. Counts above are hits, not percentages. A scene hit means temporal overlap with the labeled interval; broad passages can pass without precise localization. Some generic memories may fit multiple films or nearby passages: a miss of the single expected label does not establish that every returned alternative is irrelevant. Latencies exclude startup and were recorded under the machine’s current load.

## Every result

| ID | Movie | Category | Movie rank | Scene rank | Diagnosis |
|---|---|---|---:|---:|---|
| fresh-001 | Spider-Man | direct_dialogue | 1 | 1 | hit |
| fresh-002 | Spider-Man | imperfect_dialogue | 1 | 1 | hit |
| fresh-003 | Spider-Man | natural_description | 1 | 1 | hit |
| fresh-004 | Captain America: The First Avenger | direct_dialogue | 1 | 1 | hit |
| fresh-005 | Captain America: The First Avenger | imperfect_dialogue | 1 | 1 | hit |
| fresh-006 | Captain America: The First Avenger | long_natural_description | — | — | candidate_miss |
| fresh-007 | Thor | direct_dialogue | 1 | 1 | hit |
| fresh-008 | Thor | imperfect_dialogue | 1 | 1 | hit |
| fresh-009 | Thor | natural_description | 1 | 1 | hit |
| fresh-010 | Iron Man 3 | direct_dialogue | 1 | 1 | hit |
| fresh-011 | Iron Man 3 | imperfect_dialogue | 1 | 1 | hit |
| fresh-012 | Iron Man 3 | long_natural_description | — | — | reranking_miss |
| fresh-013 | Once Upon a Time... in Hollywood | direct_dialogue | 1 | 1 | hit |
| fresh-014 | Once Upon a Time... in Hollywood | imperfect_dialogue | 1 | 1 | hit |
| fresh-015 | Once Upon a Time... in Hollywood | natural_description | 1 | — | reranking_miss |
| fresh-016 | Iron Man 2 | direct_dialogue | 1 | 1 | hit |
| fresh-017 | Iron Man 2 | imperfect_dialogue | 1 | 1 | hit |
| fresh-018 | Iron Man 2 | long_natural_description | — | — | reranking_miss |
| fresh-019 | Prisoners | direct_dialogue | 1 | 1 | hit |
| fresh-020 | Prisoners | imperfect_dialogue | 1 | 1 | hit |
| fresh-021 | Prisoners | natural_description | 1 | 1 | hit |
| fresh-022 | The Hangover | direct_dialogue | 1 | 1 | hit |
| fresh-023 | The Hangover | imperfect_dialogue | 1 | 1 | hit |
| fresh-024 | The Hangover | long_natural_description | — | — | reranking_miss |
| fresh-025 | The Hobbit: An Unexpected Journey | direct_dialogue | 1 | 1 | hit |
| fresh-026 | The Hobbit: An Unexpected Journey | imperfect_dialogue | 1 | 1 | hit |
| fresh-027 | The Hobbit: An Unexpected Journey | natural_description | 1 | — | reranking_miss |
| fresh-028 | Captain America: Civil War | direct_dialogue | 1 | 1 | hit |
| fresh-029 | Captain America: Civil War | imperfect_dialogue | 1 | 1 | hit |
| fresh-030 | Captain America: Civil War | long_natural_description | 7 | 7 | hit |
| fresh-031 | Logan | direct_dialogue | 1 | 1 | hit |
| fresh-032 | Logan | imperfect_dialogue | 1 | 1 | hit |
| fresh-033 | Logan | natural_description | 1 | 1 | hit |
| fresh-034 | Donnie Darko | direct_dialogue | 1 | 1 | hit |
| fresh-035 | Donnie Darko | imperfect_dialogue | 1 | 1 | hit |
| fresh-036 | Donnie Darko | long_natural_description | — | — | candidate_miss |
| fresh-037 | Slumdog Millionaire | direct_dialogue | 1 | 1 | hit |
| fresh-038 | Slumdog Millionaire | imperfect_dialogue | 1 | 1 | hit |
| fresh-039 | Slumdog Millionaire | natural_description | 1 | 1 | hit |
| fresh-040 | Black Panther | direct_dialogue | 1 | 1 | hit |
| fresh-041 | Black Panther | imperfect_dialogue | 1 | 1 | hit |
| fresh-042 | Black Panther | long_natural_description | — | — | candidate_miss |
| fresh-043 | Gravity | direct_dialogue | 1 | 1 | hit |
| fresh-044 | Gravity | imperfect_dialogue | 1 | 1 | hit |
| fresh-045 | Gravity | natural_description | 2 | 2 | hit |
| fresh-046 | The Incredibles | direct_dialogue | 1 | 1 | hit |
| fresh-047 | The Incredibles | imperfect_dialogue | 1 | 1 | hit |
| fresh-048 | The Incredibles | long_natural_description | — | — | reranking_miss |
| fresh-049 | Thor: Ragnarok | direct_dialogue | 1 | 1 | hit |
| fresh-050 | Thor: Ragnarok | imperfect_dialogue | 1 | 1 | hit |
| fresh-051 | Thor: Ragnarok | natural_description | 1 | 1 | hit |
| fresh-052 | How to Train Your Dragon | direct_dialogue | 1 | 1 | hit |
| fresh-053 | How to Train Your Dragon | imperfect_dialogue | 1 | 1 | hit |
| fresh-054 | How to Train Your Dragon | long_natural_description | 7 | — | reranking_miss |
| fresh-055 | Black Swan | direct_dialogue | 1 | 1 | hit |
| fresh-056 | Black Swan | imperfect_dialogue | 1 | 1 | hit |
| fresh-057 | Black Swan | natural_description | 1 | 1 | hit |
| fresh-058 | Doctor Strange | direct_dialogue | 1 | 1 | hit |
| fresh-059 | Doctor Strange | imperfect_dialogue | 1 | 1 | hit |
| fresh-060 | Doctor Strange | long_natural_description | 5 | — | reranking_miss |
| fresh-061 | The Imitation Game | direct_dialogue | 1 | 1 | hit |
| fresh-062 | The Imitation Game | imperfect_dialogue | 1 | 1 | hit |
| fresh-063 | The Imitation Game | natural_description | — | — | candidate_miss |
| fresh-064 | I Am Legend | direct_dialogue | 1 | 1 | hit |
| fresh-065 | I Am Legend | imperfect_dialogue | 1 | 1 | hit |
| fresh-066 | I Am Legend | long_natural_description | 1 | — | reranking_miss |
| fresh-067 | Man of Steel | direct_dialogue | 1 | 1 | hit |
| fresh-068 | Man of Steel | imperfect_dialogue | 1 | 1 | hit |
| fresh-069 | Man of Steel | natural_description | 2 | 2 | hit |
| fresh-070 | Gran Torino | direct_dialogue | 1 | 1 | hit |
| fresh-071 | Gran Torino | imperfect_dialogue | 1 | 1 | hit |
| fresh-072 | Gran Torino | long_natural_description | 3 | 3 | hit |
| fresh-073 | Guardians of the Galaxy Vol. 2 | direct_dialogue | 1 | 1 | hit |
| fresh-074 | Guardians of the Galaxy Vol. 2 | imperfect_dialogue | 1 | 1 | hit |
| fresh-075 | Guardians of the Galaxy Vol. 2 | natural_description | — | — | candidate_miss |
| fresh-076 | John Wick | direct_dialogue | 1 | 1 | hit |
| fresh-077 | John Wick | imperfect_dialogue | 1 | 1 | hit |
| fresh-078 | John Wick | long_natural_description | — | — | reranking_miss |
| fresh-079 | Pirates of the Caribbean: Dead Man's Chest | direct_dialogue | 1 | 1 | hit |
| fresh-080 | Pirates of the Caribbean: Dead Man's Chest | imperfect_dialogue | 1 | 1 | hit |
| fresh-081 | Pirates of the Caribbean: Dead Man's Chest | natural_description | 1 | 1 | hit |
| fresh-082 | Sin City | direct_dialogue | 1 | 1 | hit |
| fresh-083 | Sin City | imperfect_dialogue | 1 | 1 | hit |
| fresh-084 | Sin City | long_natural_description | 4 | 4 | hit |
| fresh-085 | The Social Network | direct_dialogue | 1 | 1 | hit |
| fresh-086 | The Social Network | imperfect_dialogue | 1 | 1 | hit |
| fresh-087 | The Social Network | natural_description | 1 | 1 | hit |
| fresh-088 | Dunkirk | direct_dialogue | 1 | 1 | hit |
| fresh-089 | Dunkirk | imperfect_dialogue | 1 | 1 | hit |
| fresh-090 | Dunkirk | long_natural_description | 10 | — | reranking_miss |
| fresh-091 | Edge of Tomorrow | direct_dialogue | 1 | 1 | hit |
| fresh-092 | Edge of Tomorrow | imperfect_dialogue | 1 | 1 | hit |
| fresh-093 | Edge of Tomorrow | natural_description | 1 | 1 | hit |
| fresh-094 | Spider-Man: Homecoming | direct_dialogue | 1 | 1 | hit |
| fresh-095 | Spider-Man: Homecoming | imperfect_dialogue | 1 | 1 | hit |
| fresh-096 | Spider-Man: Homecoming | long_natural_description | — | — | reranking_miss |
| fresh-097 | Batman v Superman: Dawn of Justice | direct_dialogue | 1 | 1 | hit |
| fresh-098 | Batman v Superman: Dawn of Justice | imperfect_dialogue | 1 | 1 | hit |
| fresh-099 | Batman v Superman: Dawn of Justice | natural_description | 5 | 5 | hit |
| fresh-100 | X-Men: Days of Future Past | direct_dialogue | 1 | 1 | hit |
| fresh-101 | X-Men: Days of Future Past | imperfect_dialogue | 1 | 1 | hit |
| fresh-102 | X-Men: Days of Future Past | long_natural_description | — | — | reranking_miss |
| fresh-103 | 12 Years a Slave | direct_dialogue | 1 | 1 | hit |
| fresh-104 | 12 Years a Slave | imperfect_dialogue | 1 | 1 | hit |
| fresh-105 | 12 Years a Slave | natural_description | 1 | 1 | hit |
| fresh-106 | Spider-Man: Into the Spider-Verse | direct_dialogue | 1 | 1 | hit |
| fresh-107 | Spider-Man: Into the Spider-Verse | imperfect_dialogue | 1 | 1 | hit |
| fresh-108 | Spider-Man: Into the Spider-Verse | long_natural_description | — | — | reranking_miss |
| fresh-109 | Spider-Man 2 | direct_dialogue | 1 | 1 | hit |
| fresh-110 | Spider-Man 2 | imperfect_dialogue | 1 | 1 | hit |
| fresh-111 | Spider-Man 2 | natural_description | — | — | shortlist_excluded |
| fresh-112 | World War Z | direct_dialogue | 1 | 1 | hit |
| fresh-113 | World War Z | imperfect_dialogue | 1 | 1 | hit |
| fresh-114 | World War Z | long_natural_description | — | — | reranking_miss |
| fresh-115 | Ant-Man | direct_dialogue | 1 | 1 | hit |
| fresh-116 | Ant-Man | imperfect_dialogue | 1 | 1 | hit |
| fresh-117 | Ant-Man | natural_description | 1 | 1 | hit |
| fresh-118 | Thor: The Dark World | direct_dialogue | 1 | 1 | hit |
| fresh-119 | Thor: The Dark World | imperfect_dialogue | 1 | 1 | hit |
| fresh-120 | Thor: The Dark World | long_natural_description | — | — | reranking_miss |
| fresh-121 | Spider-Man | visual_memory | — | — | visual_or_movie_miss |
| fresh-122 | Captain America: The First Avenger | visual_memory | 1 | — | movie_only_unverified |
| fresh-123 | Thor | visual_memory | 1 | — | movie_only_unverified |
| fresh-124 | Iron Man 3 | visual_memory | — | — | visual_or_movie_miss |
| fresh-125 | Once Upon a Time... in Hollywood | visual_memory | 1 | — | movie_only_unverified |
| fresh-126 | Iron Man 2 | visual_memory | — | — | visual_or_movie_miss |
| fresh-127 | Prisoners | visual_memory | 6 | — | movie_only_unverified |
| fresh-128 | The Hangover | visual_memory | 1 | — | movie_only_unverified |
| fresh-129 | The Hobbit: An Unexpected Journey | visual_memory | 1 | — | movie_only_unverified |
| fresh-130 | Captain America: Civil War | visual_memory | — | — | visual_or_movie_miss |
| fresh-131 | Logan | visual_memory | 1 | — | movie_only_unverified |
| fresh-132 | Donnie Darko | visual_memory | — | — | visual_or_movie_miss |
| fresh-133 | Slumdog Millionaire | visual_memory | — | — | visual_or_movie_miss |
| fresh-134 | Black Panther | visual_memory | 1 | — | movie_only_unverified |
| fresh-135 | Gravity | visual_memory | 5 | — | movie_only_unverified |
| fresh-136 | The Incredibles | visual_memory | — | — | visual_or_movie_miss |
| fresh-137 | Thor: Ragnarok | visual_memory | 1 | — | movie_only_unverified |
| fresh-138 | How to Train Your Dragon | visual_memory | 2 | — | movie_only_unverified |
| fresh-139 | Black Swan | visual_memory | — | — | visual_or_movie_miss |
| fresh-140 | Doctor Strange | visual_memory | — | — | visual_or_movie_miss |
| fresh-141 | The Imitation Game | visual_memory | 2 | — | movie_only_unverified |
| fresh-142 | I Am Legend | visual_memory | — | — | visual_or_movie_miss |
| fresh-143 | Man of Steel | visual_memory | — | — | visual_or_movie_miss |
| fresh-144 | Gran Torino | visual_memory | 3 | — | movie_only_unverified |
| fresh-145 | Guardians of the Galaxy Vol. 2 | visual_memory | — | — | visual_or_movie_miss |
| fresh-146 | John Wick | visual_memory | 1 | — | movie_only_unverified |
| fresh-147 | Pirates of the Caribbean: Dead Man's Chest | visual_memory | — | — | visual_or_movie_miss |
| fresh-148 | Sin City | visual_memory | — | — | visual_or_movie_miss |
| fresh-149 | The Social Network | visual_memory | 2 | — | movie_only_unverified |
| fresh-150 | Dunkirk | visual_memory | 1 | — | movie_only_unverified |

## Every top-five miss

Full query text, expected dialogue, retrieval-channel ranks, and the first three returned passages are preserved in `fresh150_failures.json`. Missing ranks mean absent from the returned top ten, not proof that the movie is absent from the corpus.

### fresh-006: Captain America: The First Avenger (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A skinny volunteer has just come out of a scientific experiment looking much bigger. Someone asks how he feels and he jokes about his new height. The celebration is suddenly interrupted by a shooting and a man trying to get away.

Movie rank: None; scene rank: None; diagnosis: candidate_miss. Candidate retained: False; reranked: False.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": null, "plot_guided": null}`.

### fresh-012: Iron Man 3 (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: Two men in armored superhero suits are arguing about computer security. One needs the other's login, and the embarrassing password is based on his old superhero name with a deliberately cool spelling and capital letters.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 33, "all_clues": null, "quote_fragments": null, "semantic": 74, "tail_clues": 1, "plot_guided": null}`.

### fresh-015: Once Upon a Time... in Hollywood (natural_description)

A stuntman visits an old colleague at a ranch and has to wake him up. The old man cannot place who he is and confuses his name with a historical assassin. The visitor reminds him about the television western they used to make there.

Movie rank: 1; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 3, "all_clues": null, "quote_fragments": null, "semantic": 19, "plot_guided": null}`.

### fresh-018: Iron Man 2 (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: An arms manufacturer suddenly learns that the robots he is presenting are no longer under his control. The software has been replaced, the guards cannot be reached by phone, and even the mobile phones and security systems have stopped working.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": 9, "tail_clues": 1, "plot_guided": null}`.

### fresh-024: The Hangover (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: Some men with missing memories go to a doctor. One insists that he is a medical professional too, but the doctor reminds him that he is only a dentist. Blood-test results explain that somebody gave them a drug that causes blackouts.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": 20, "tail_clues": 1, "plot_guided": null}`.

### fresh-027: The Hobbit: An Unexpected Journey (natural_description)

An unexpected bearded guest walks straight into a small man's home. They introduce themselves very formally, but the homeowner has no idea why he is there. The stranger is much more interested in finding the promised dinner and eating everything.

Movie rank: 1; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": null, "plot_guided": null}`.

### fresh-030: Captain America: Civil War (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A wealthy superhero admits that he keeps failing the woman he loves. He says he destroyed his suits once, but there was always another crisis and another fight. He considers whether signing an agreement might help save the relationship.

Movie rank: 7; scene rank: 7; diagnosis: ranked_below_top5. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 1, "plot_guided": null}`.

### fresh-036: Donnie Darko (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A woman tells another mother that she refuses to believe the accusations against a local self-help celebrity. She insists he is being persecuted and plans to organize his legal defense, which leaves somebody else responsible for a school trip.

Movie rank: None; scene rank: None; diagnosis: candidate_miss. Candidate retained: False; reranked: False.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": null, "plot_guided": null}`.

### fresh-042: Black Panther (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A masked rescuer meets a woman during her mission and is momentarily distracted by seeing her again. She is annoyed that he has interfered. He tells her his father has died and asks her to come home for his coronation.

Movie rank: None; scene rank: None; diagnosis: candidate_miss. Candidate retained: False; reranked: False.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": null, "plot_guided": null}`.

### fresh-048: The Incredibles (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A superhero mother has to leave her two children alone while she looks for their father. She puts the older girl in charge, tells them to conceal their identities, and gives permission to use the powers she normally insists they hide.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 10, "plot_guided": null}`.

### fresh-054: How to Train Your Dragon (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A young trainee finds a dangerous black dragon trapped and helpless. Killing it would prove that he belongs with the warriors of his village, but he hesitates when he finally has the chance to finish it off.

Movie rank: 7; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 7, "all_clues": null, "quote_fragments": null, "semantic": 23, "tail_clues": 8, "plot_guided": 10}`.

### fresh-060: Doctor Strange (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A magic student is shown a hidden copy of the world where their actions do not affect ordinary reality. His teacher explains that they practice there and can trap dangers there, but warns him never to lose the ring that would let him get out.

Movie rank: 5; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": 18, "tail_clues": 1, "plot_guided": null}`.

### fresh-063: The Imitation Game (natural_description)

Police discussing an investigation discover that their suspect is involved with another man. One officer wants to pursue the important work the suspect was doing, but another insists on arresting him for his private life instead.

Movie rank: None; scene rank: None; diagnosis: candidate_miss. Candidate retained: False; reranked: False.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "plot_guided": null}`.

### fresh-066: I Am Legend (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A lonely survivor repeats a radio message offering other people food, somewhere to stay, and protection. He says exactly where he will wait every day when the sun is overhead and begs anyone still alive to answer him.

Movie rank: 1; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 13, "all_clues": null, "quote_fragments": null, "semantic": 129, "tail_clues": 1, "plot_guided": null}`.

### fresh-075: Guardians of the Galaxy Vol. 2 (natural_description)

A huge literal-minded man keeps explaining why he is not attracted to a strange young woman. She is frustrated because she is trying to warn him about a dangerous plan, while he keeps interpreting the conversation as romantic interest.

Movie rank: None; scene rank: None; diagnosis: candidate_miss. Candidate retained: False; reranked: False.

Expected-scene channel ranks: `{"keyword": 145, "all_clues": null, "quote_fragments": null, "semantic": null, "plot_guided": null}`.

### fresh-078: John Wick (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A stranger admires a retired man's vintage muscle car at a petrol station and asks how much he wants for it. The owner refuses to sell. His dog is with him, and the conversation carries a threat that the stranger does not yet understand.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 1, "plot_guided": null}`.

### fresh-090: Dunkirk (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: Soldiers who have just escaped an attack are ushered onto a boat. Helpers tell them to keep moving down below, hand out blankets, and promise them hot tea. Everyone is trying to squeeze aboard and get away safely.

Movie rank: 10; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": 2, "tail_clues": 1, "plot_guided": null}`.

### fresh-096: Spider-Man: Homecoming (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A teenager's enthusiastic friend tells him that an older girl likes him and that being associated with a superhero team should help his chances. They prepare to go to her house party, and the friend is proud of the hat he is wearing.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": 2, "tail_clues": 1, "plot_guided": null}`.

### fresh-102: X-Men: Days of Future Past (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: Someone explains that killing a scientist made the mutant problem worse. The killer was captured and experimented on, and the secrets in her body allowed machines to adapt to the powers of the people they hunted.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 10, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 1, "plot_guided": null}`.

### fresh-108: Spider-Man: Into the Spider-Verse (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A father stands outside his teenage son's locked bedroom and asks him to open up. He can see the boy's shadow but gets no answer. He tells him that he does not want them to grow apart and tries to express his love without forcing the door.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 1, "plot_guided": null}`.

### fresh-111: Spider-Man 2 (natural_description)

At a public event a rich young man lashes out at his oldest friend. He accuses him of siding with a masked hero, taking the woman he loved, and stealing his father's affection. His jealousy and grief make the confrontation increasingly embarrassing.

Movie rank: None; scene rank: None; diagnosis: shortlist_excluded. Candidate retained: True; reranked: False.

Expected-scene channel ranks: `{"keyword": 33, "all_clues": null, "quote_fragments": null, "semantic": null, "plot_guided": null}`.

### fresh-114: World War Z (long_natural_description)

I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: A man investigating a deadly outbreak suggests that the attackers avoid people who are already sick. Others think infecting soldiers deliberately sounds insane. He explains that illness would hide them from the creatures rather than cure the outbreak.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 142, "all_clues": null, "quote_fragments": null, "semantic": 1, "tail_clues": 1, "plot_guided": null}`.

### fresh-120: Thor: The Dark World (long_natural_description)

I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: A young woman collects a scientist from police custody and pretends to be his daughter. The officer lists his wallet, keys, medication, and embarrassing clothing among his possessions. She has also seen the strange things he did on television.

Movie rank: None; scene rank: None; diagnosis: reranking_miss. Candidate retained: True; reranked: True.

Expected-scene channel ranks: `{"keyword": 1, "all_clues": null, "quote_fragments": null, "semantic": null, "tail_clues": 1, "plot_guided": null}`.

### fresh-121: Spider-Man (visual_memory)

A masked hero hangs upside down in the rain while a woman rolls his mask partway up and kisses him.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-124: Iron Man 3 (visual_memory)

Dozens of empty metal superhero suits arrive at an industrial site and start fighting while their owner jumps between them.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-126: Iron Man 2 (visual_memory)

Two armored men battle remotely controlled robots together in a landscaped garden at night.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-127: Prisoners (visual_memory)

A desperate father holds a young suspect captive in an abandoned building and tortures him because he thinks he knows where his daughter is.

Movie rank: 6; scene rank: None; diagnosis: ranked_below_top5. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-130: Captain America: Civil War (visual_memory)

Two former allies fight at an airport while a teenage hero helps one side and another fighter grows much taller than the planes.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-132: Donnie Darko (visual_memory)

An enormous aircraft engine falls through the roof of a teenage boy's bedroom during the night.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-133: Slumdog Millionaire (visual_memory)

Two children flee across rooftops and through a crowded slum while a policeman tries to catch them.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-136: The Incredibles (visual_memory)

A superhero runs across the surface of the ocean by freezing a path under his feet, then slides along a track of ice.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-139: Black Swan (visual_memory)

A ballerina performs under stage lights while imagining black feathers growing from her skin and wings spreading from her arms.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-140: Doctor Strange (visual_memory)

Buildings bend and rotate around two men as they fight through a city whose streets seem to fold in on themselves.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-142: I Am Legend (visual_memory)

A lone man drives through deserted city streets hunting deer from his car while his dog accompanies him.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-143: Man of Steel (visual_memory)

A man chooses to remain in the path of a tornado and signals his son to stay back rather than reveal his powers.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-145: Guardians of the Galaxy Vol. 2 (visual_memory)

A tiny tree-like creature dances to music while a team fights a huge tentacled monster in the background.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-147: Pirates of the Caribbean: Dead Man's Chest (visual_memory)

Sailors duel on a giant wooden waterwheel that breaks free and rolls down a hill with the fighters still on it.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

### fresh-148: Sin City (visual_memory)

A heavily bandaged man keeps fighting his way through a violent city while remembering a murdered woman he spent one night with.

Movie rank: None; scene rank: None; diagnosis: visual_or_movie_miss. Candidate retained: None; reranked: None.

Expected-scene channel ranks: `{"keyword": null, "all_clues": null, "semantic": null, "plot_guided": null}`.

## Twenty additional paired controls

The same twenty long-description events were also tested as concise descriptions, with no search changes. Completed: 20/20; scene Hit@5: 15; movie Hit@5: 17. Removing the preamble gained 13 scene hits and lost 0. These comparisons isolate the supplied preamble on these selected examples; they do not prove a universal effect of query length.

| Movie | Long scene rank | Concise scene rank |
|---|---:|---:|
| Captain America: The First Avenger | — | 8 |
| Iron Man 3 | — | 1 |
| Iron Man 2 | — | 3 |
| The Hangover | — | 1 |
| Captain America: Civil War | 7 | 1 |
| Donnie Darko | — | — |
| Black Panther | — | 10 |
| The Incredibles | — | — |
| How to Train Your Dragon | — | 6 |
| Doctor Strange | — | 4 |
| I Am Legend | — | 1 |
| Gran Torino | 3 | 1 |
| John Wick | — | 3 |
| Sin City | 4 | 4 |
| Dunkirk | — | 1 |
| Spider-Man: Homecoming | — | 3 |
| X-Men: Days of Future Past | — | 1 |
| Spider-Man: Into the Spider-Verse | — | 1 |
| World War Z | — | 1 |
| Thor: The Dark World | — | 2 |

## Label review

Visual-memory labels are exploratory and were not verified against video. Raw scores retain all frozen labels, including the following uncertain example; no query was removed or relabeled to improve the result.

- fresh-136: The ocean detail in this manually authored memory is not established by the consulted official character pages and may conflate installments. Preserve the frozen query and raw outcome; treat this movie label as tentative, not verified ground truth. [Official source 1](https://www.pixar.com/the-incredibles), [Official source 2](https://movies.disney.com/the-incredibles)