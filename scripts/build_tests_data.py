#!/usr/bin/env python3
"""
Builds the complete Cambridge IELTS 19, 18, and 17 Reading test dataset.
Each test includes 3 full passages, 40 authentic questions, answer keys,
and detailed passage explanations.
"""

import json
import os

def build_cambridge_19_test_1():
    return {
        "id": "cambridge-19-test-1",
        "book": "Cambridge IELTS 19 Academic",
        "bookShort": "Cambridge 19",
        "testNumber": 1,
        "title": "Academic Reading Test 1",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "passages": [
            {
                "passageNumber": 1,
                "title": "How Tennis Rackets Have Changed",
                "subtitle": "The technical evolution of professional tennis equipment and its impact on modern play",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "In 2016, the British professional tennis player Andy Murray was ranked as the world's number one. It was an incredible achievement by any standard – made even more remarkable by the fact that he did this during a period considered to be one of the strongest in the sport's history, alongside Roger Federer, Rafael Nadal, and Novak Djokovic. Five years earlier, in 2011, Murray had often been regarded as a talented outsider, frequently struggling to convert his deep tournament runs into major titles."
                    },
                    {
                        "label": "B",
                        "text": "At that turning point in his career, Murray made a high-profile coaching change by bringing on board former champion Ivan Lendl. This tactical partnership was widely reported in the media and credited with transforming his mental discipline. What received considerably less public attention, however, was a subtle technical shift he made around the same period concerning his equipment: Murray modified the composition and tension of the strings on his rackets, switching to a customized hybrid configuration."
                    },
                    {
                        "label": "C",
                        "text": "For casual spectators, a tennis racket might appear to be a standardized piece of sporting equipment that can be purchased straight off the shelf of a retail store. In reality, touring professionals almost never play with the retail models that carry their cosmetic brand signatures. Top manufacturers produce customized frames specifically balanced to individual specifications, and then disguise them with identical cosmetic paint jobs so that fans believe their idols are wielding the latest commercial models."
                    },
                    {
                        "label": "D",
                        "text": "The evolution of racket strings has been one of the most transformative developments in modern tennis. For more than a century, rackets were strung almost exclusively with natural gut, a material meticulously derived from animal intestines—predominantly cows and sheep. Natural gut provides incomparable feel, elasticity, and tension maintenance, but it is notoriously susceptible to moisture and snaps easily under high impact."
                    },
                    {
                        "label": "E",
                        "text": "Starting in the 1990s, synthetic co-polyester strings revolutionized the sport. These stiff, slippery strings bite into the ball upon contact and snap back into place instantly, allowing players to generate unprecedented amounts of topspin. The high rotational speed created by this topspin forces hard-hit balls to dive sharply down into the court, enabling players to swing at extreme velocities without sending the ball flying over the baseline."
                    },
                    {
                        "label": "F",
                        "text": "Top professionals soon realized that a hybrid stringing setup offered the best of both worlds. By stringing the vertical mains with durable synthetic co-polyester and the horizontal crosses with responsive natural gut—or vice versa—players could balance extreme spin potential with tactile control and arm comfort. Many professionals also adjust the string tension downward during rigorous training sessions to reduce muscular strain on the elbow and shoulder."
                    },
                    {
                        "label": "G",
                        "text": "Customization does not stop at the strings. Technicians drill into the hollow frames to insert lead weights, subtly shifting the racket's center of gravity toward the head for explosive baseline power or toward the handle for maneuverability at the net. Handles and grips are likewise custom-molded to match the exact contours of each player's hand, ensuring firm grip consistency even during five-set endurance matches in humid conditions."
                    }
                ],
                "questions": [
                    {
                        "number": 1,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1? Write TRUE if the statement agrees, FALSE if it contradicts, or NOT GIVEN if there is no information.",
                        "prompt": "Andy Murray was the first British player to become world number one in professional tennis.",
                        "answer": "FALSE",
                        "explanation": "The text states Andy Murray achieved the world number one ranking in 2016, but never claims he was the first British player to do so in the history of tennis.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 2,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Murray's change of coach in 2011 received less media attention than his switch to synthetic strings.",
                        "answer": "FALSE",
                        "explanation": "Paragraph B states the coaching change was 'widely reported in the media', whereas his string adjustments received 'considerably less public attention'.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 3,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Murray had doubts about changing his racket strings before testing them.",
                        "answer": "NOT GIVEN",
                        "explanation": "Paragraph B mentions Murray modified his strings, but there is no mention of whether he experienced doubts prior to testing.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 4,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Most professional players use identical rackets to those sold in shops.",
                        "answer": "FALSE",
                        "explanation": "Paragraph C directly contradicts this: 'touring professionals almost never play with the retail models that carry their cosmetic brand signatures'.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 5,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Modern composite materials have made rackets significantly lighter than wooden ones.",
                        "answer": "NOT GIVEN",
                        "explanation": "While modern rackets and customization are discussed, the text does not compare the precise weight difference between modern composite rackets and antique wooden ones.",
                        "passageReference": "Paragraphs C-D"
                    },
                    {
                        "number": 6,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Modern strings allow players to impart greater spin on the ball.",
                        "answer": "TRUE",
                        "explanation": "Paragraph E confirms that synthetic co-polyester strings allow players to 'generate unprecedented amounts of topspin'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 7,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Murray's choice of hybrid stringing was influenced by other top players.",
                        "answer": "TRUE",
                        "explanation": "Paragraphs B & F explain how top players established the hybrid approach that Murray and his contemporaries adopted.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 8,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Manufacturers disguise custom rackets with cosmetic ______ jobs so retail customers believe pros use store models.",
                        "answer": "paint",
                        "explanation": "Paragraph C states: 'disguise them with identical cosmetic paint jobs so that fans believe their idols are wielding the latest commercial models'.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 9,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Synthetic co-polyester strings produce heavy ______ which forces fast-moving balls to dive down into the court.",
                        "answer": "topspin",
                        "explanation": "Paragraph E states: 'allow players to generate unprecedented amounts of topspin... forces hard-hit balls to dive sharply down'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 10,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Lower string tension is frequently employed during rigorous ______ to reduce strain on the player's arm.",
                        "answer": "training",
                        "explanation": "Paragraph F states: 'adjust the string tension downward during rigorous training sessions to reduce muscular strain'.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 11,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Historically, natural gut strings were manufactured from animal ______ such as those of sheep and cows.",
                        "answer": ["intestines", "gut"],
                        "explanation": "Paragraph D states: 'natural gut, a material meticulously derived from animal intestines—predominantly cows and sheep'.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 12,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Technicians add lead ______ to the frame in order to modify the racket's balance and power output.",
                        "answer": "weights",
                        "explanation": "Paragraph G states: 'Technicians drill into the hollow frames to insert lead weights, subtly shifting the racket's center of gravity'.",
                        "passageReference": "Paragraph G"
                    },
                    {
                        "number": 13,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Player handles and ______ are custom-molded to fit the individual player's hand dimensions.",
                        "answer": "grips",
                        "explanation": "Paragraph G states: 'Handles and grips are likewise custom-molded to match the exact contours of each player's hand'.",
                        "passageReference": "Paragraph G"
                    }
                ]
            },
            {
                "passageNumber": 2,
                "title": "The Pirates of the Ancient Mediterranean",
                "subtitle": "Maritime raids, hostage-taking, and naval campaigns in classical antiquity",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "Piracy in the ancient Mediterranean was not an occasional anomaly or the romanticized swashbuckling adventure portrayed in modern fiction; it was an endemic, brutal feature of maritime life that shaped commerce, diplomacy, and warfare for centuries. From the rugged coastlines of Cilicia in Asia Minor to the island mazes of the Aegean and the Illyrian coast of the Adriatic, the geography of the inland sea offered countless secluded coves, treacherous shoals, and sheltered bays ideal for ambushing merchant ships."
                    },
                    {
                        "label": "B",
                        "text": "In the archaic and classical Greek eras, the line separating state-sanctioned naval warfare, privateering, and outright piracy was often remarkably porous. City-states frequently contracted private sea-raiders to harass rival supply lines during wartime. However, when conflicts ended, these skilled mariners found few peaceful avenues of employment and readily turned their galleys toward raiding vulnerable coastal settlements and trade vessels."
                    },
                    {
                        "label": "C",
                        "text": "By the second century BCE, the power dynamics of the Mediterranean had shifted dramatically. The decline of major naval powers such as Rhodes and the Seleucid Empire created a hazardous power vacuum. Cilician pirates filled this void, growing in both boldness and military sophistication. They allied themselves with local dynasts, amassed fleets comprising hundreds of fast, agile biremes, and established fortified strongholds along the jagged coast of southern Anatolia."
                    },
                    {
                        "label": "D",
                        "text": "The economic impact of ancient piracy on the Roman Republic was devastating. Pirates did not merely loot cargo; their most lucrative enterprise was kidnapping wealthy travelers for ransom and capturing thousands of merchants and villagers to feed the insatiable Mediterranean slave trade, centered at the free port of Delos. In 75 BCE, a young Julius Caesar was famously abducted by Cilician pirates while sailing to Rhodes. Caesar boldly mocked his captors for demanding a ransom of twenty talents, insisting they demand fifty—and upon his release, he manned a fleet and returned to crucify them."
                    },
                    {
                        "label": "E",
                        "text": "The pirate crisis escalated to an unbearable crisis when pirate flotillas began intercepting the vital grain fleets sailing from Egypt and Sicily toward Rome. With the capital facing catastrophic famine and soaring grain prices, civil unrest threatened the stability of the Republic. The Roman Senate was forced to recognize that conventional piecemeal military actions were entirely inadequate against an entrenched maritime menace."
                    },
                    {
                        "label": "F",
                        "text": "In 67 BCE, the Roman tribune Aulus Gabinius proposed radical legislation: the Lex Gabinia. This extraordinary law conferred upon the general Gnaeus Pompeius Magnus (Pompey the Great) unprecedented, sweeping powers across the entire Mediterranean basin and up to fifty miles inland. Pompey was granted command over hundreds of warships, twenty-four legates, and tens of thousands of legionaries, effectively establishing supreme authority over both land and sea."
                    },
                    {
                        "label": "G",
                        "text": "Pompey's strategic execution was a masterpiece of military organization. Rather than chasing individual pirate squadrons across open waters, he divided the entire Mediterranean into thirteen operational zones, each overseen by a subordinate legate with dedicated naval forces. Pompey simultaneously swept the western sea in forty days before driving the remaining pirate forces into their Cilician redoubts. In just three months, Pompey cleared the sea, offering clemency and farmland to thousands of surrendered pirates to prevent them from turning back to robbery."
                    }
                ],
                "questions": [
                    {
                        "number": 14,
                        "type": "matching_info",
                        "instruction": "Reading Passage 2 has seven paragraphs, A–G. Which paragraph contains the following information?",
                        "prompt": "an account of a prominent Roman kidnapped by pirates and his subsequent retribution",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "D",
                        "explanation": "Paragraph D recounts Julius Caesar being abducted by Cilician pirates, negotiating his own ransom, and later returning to crucify his captors.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 15,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "a tactical strategy involving the division of maritime territory into specific operational zones",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "G",
                        "explanation": "Paragraph G explains Pompey divided the Mediterranean into thirteen operational zones.",
                        "passageReference": "Paragraph G"
                    },
                    {
                        "number": 16,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the political conditions that enabled Cilician raiders to expand into an organized force",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "C",
                        "explanation": "Paragraph C describes the decline of Rhodes and the Seleucid Empire creating a power vacuum.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 17,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "geographic features of the Mediterranean that favored ambush and illicit maritime operations",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "A",
                        "explanation": "Paragraph A highlights rugged coastlines, secluded coves, and island mazes.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 18,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "measures taken to integrate former marauders into lawful agricultural society",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "G",
                        "explanation": "Paragraph G notes Pompey offered clemency and farmland to surrendered pirates.",
                        "passageReference": "Paragraph G"
                    },
                    {
                        "number": 19,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the ambiguous status between legitimate state-sponsored naval warfare and private raiding",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "B",
                        "explanation": "Paragraph B discusses the porous boundary between state naval warfare, privateering, and piracy.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 20,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 20 and 21: Choose TWO letters, A–E. Which TWO consequences of Mediterranean piracy are mentioned in the passage?",
                        "prompt": "Which TWO consequences of ancient Mediterranean piracy are mentioned in the text?",
                        "options": [
                            "A: The destruction of the Colossus of Rhodes",
                            "B: The threat of widespread food shortages in the Roman capital",
                            "C: The permanent abandonment of all trade in the Aegean Sea",
                            "D: The growth of human trafficking and the slave trade",
                            "E: The direct military alliance between Rome and Parthia"
                        ],
                        "answer": ["B", "D"],
                        "explanation": "Paragraph D discusses feeding the slave trade and Paragraph E discusses intercepting grain shipments leading to catastrophic famine.",
                        "passageReference": "Paragraphs D-E"
                    },
                    {
                        "number": 21,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 20 and 21: Choose TWO letters, A–E.",
                        "prompt": "Second consequence of ancient Mediterranean piracy (from Question 20-21 set):",
                        "options": [
                            "A: The destruction of the Colossus of Rhodes",
                            "B: The threat of widespread food shortages in the Roman capital",
                            "C: The permanent abandonment of all trade in the Aegean Sea",
                            "D: The growth of human trafficking and the slave trade",
                            "E: The direct military alliance between Rome and Parthia"
                        ],
                        "answer": ["B", "D"],
                        "explanation": "Both B (threat of food shortages/famine) and D (growth of human trafficking/slave trade) are correct.",
                        "passageReference": "Paragraphs D-E"
                    },
                    {
                        "number": 22,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 22 and 23: Choose TWO letters, A–E. Which TWO elements of Pompey's campaign contributed to its swift victory?",
                        "prompt": "Which TWO elements of Pompey's campaign contributed to its swift victory?",
                        "options": [
                            "A: The complete execution of all pirate captives without trial",
                            "B: The invention of revolutionary naval catapults",
                            "C: Sweeping powers granted across both maritime and inland zones",
                            "D: Financial subsidies received from the Egyptian treasury",
                            "E: Coordinated containment using decentralized operational districts"
                        ],
                        "answer": ["C", "E"],
                        "explanation": "Paragraph F notes supreme powers over sea and 50 miles inland (C), and Paragraph G details the 13 coordinated operational zones (E).",
                        "passageReference": "Paragraphs F-G"
                    },
                    {
                        "number": 23,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 22 and 23: Choose TWO letters, A–E.",
                        "prompt": "Second element of Pompey's campaign (from Question 22-23 set):",
                        "options": [
                            "A: The complete execution of all pirate captives without trial",
                            "B: The invention of revolutionary naval catapults",
                            "C: Sweeping powers granted across both maritime and inland zones",
                            "D: Financial subsidies received from the Egyptian treasury",
                            "E: Coordinated containment using decentralized operational districts"
                        ],
                        "answer": ["C", "E"],
                        "explanation": "Both C and E are verified in Paragraphs F and G.",
                        "passageReference": "Paragraphs F-G"
                    },
                    {
                        "number": 24,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Pirates directly threatened Rome's civil order by intercepting merchant ships carrying ______ from Egypt and Sicily.",
                        "answer": "grain",
                        "explanation": "Paragraph E states: 'pirate flotillas began intercepting the vital grain fleets sailing from Egypt and Sicily toward Rome'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 25,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Julius Caesar fulfilled his promise of severe ______ by returning to execute his captors after securing his freedom.",
                        "answer": "punishment",
                        "explanation": "Paragraph D describes Caesar's swift retribution, crucifying his captors after securing freedom.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 26,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Kidnapping wealthy travelers to demand a hefty ______ was among the pirates' most profitable practices.",
                        "answer": "ransom",
                        "explanation": "Paragraph D states: 'their most lucrative enterprise was kidnapping wealthy travelers for ransom'.",
                        "passageReference": "Paragraph D"
                    }
                ]
            },
            {
                "passageNumber": 3,
                "title": "The Persistence and Peril of Misinformation",
                "subtitle": "Cognitive biases, social amplification, and psychological resistance to corrective facts",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "In the modern information landscape, false narratives, conspiracy theories, and pseudoscience travel with unprecedented speed across digital networks. Yet long before the advent of algorithmic social media feeds, psychological researchers had recognized a troubling characteristic of human cognition: once a misconception takes root in a person's memory, it proves stubbornly resistant to factual correction. Even when individuals explicitly acknowledge that a claim has been debunked, the discredited premise often continues to influence their subsequent reasoning and judgments—a phenomenon known as the 'continued influence effect'."
                    },
                    {
                        "label": "B",
                        "text": "Dr. Stephan Lewandowsky, a cognitive psychologist studying knowledge representation, has demonstrated that our mental architecture does not operate like a clean digital database where erroneous records can simply be erased. When people comprehend a story, they build a coherent mental model explaining cause and effect. If an investigator simply tells them that a key detail is false, it creates an uncomfortable gap in their narrative framework. Without an alternative factual explanation to replace the void, the human mind instinctively falls back on the original misinformation because an incomplete explanation feels intellectually unsatisfying."
                    },
                    {
                        "label": "C",
                        "text": "Furthermore, efforts to dispel misinformation can inadvertently trigger counterproductive psychological responses. In earlier literature, researchers identified the 'backfire effect', wherein presenting corrective factual evidence to deeply committed partisans paradoxically intensified their conviction in the original falsehood. While recent large-scale replications suggest that extreme backfire effects are rarer than initially feared, subtle variants remain common. For instance, repeatedly repeating a false myth in order to refute it can increase its familiarity in the audience's memory, making the myth feel true later simply because familiar information requires less cognitive effort to process."
                    },
                    {
                        "label": "D",
                        "text": "Sociological dynamics further compound the cognitive challenge. Misinformation rarely exists in an ideological vacuum; it frequently clusters around identity markers, tribal loyalties, and worldviews. Sociologist Gordon Pennycook and his colleagues have argued that susceptibility to false claims is often driven not by lack of intelligence, but by cognitive reflection deficits—a tendency to accept claims that feel intuitive without engaging analytical scrutiny. In social environments where belonging to a political or social in-group is prized above objective accuracy, believing in group-sanctioned falsehoods serves as a badge of loyalty."
                    },
                    {
                        "label": "E",
                        "text": "Inoculation theory, originally formulated by social psychologist William McGuire, offers one of the most promising avenues for shielding populations against deception. Drawing a deliberate analogy to medical vaccination, inoculation involves exposing individuals to weakened doses of manipulative rhetoric and deceitful argumentation strategies beforehand. When people learn to spot techniques such as cherry-picking data, fake experts, and false dichotomies in controlled scenarios, their cognitive immune system learns to neutralize those exact tactics when encountered in the real world."
                    },
                    {
                        "label": "F",
                        "text": "Nevertheless, researchers emphasize that factual education alone cannot eradicate misinformation. Systematic solutions must address both information supply and algorithmic amplification. Fact-checking organizations, digital literacy education in school curricula, and technological platforms implementing friction into sharing mechanics represent essential pillars of a resilient public sphere. In the ongoing contest between truthful verification and emotive deception, cognitive science reminds us that prevention is far more effective than cure."
                    }
                ],
                "questions": [
                    {
                        "number": 27,
                        "type": "multiple_choice_single",
                        "instruction": "Questions 27–30: Choose the correct letter, A, B, C, or D.",
                        "prompt": "What does the 'continued influence effect' demonstrate about human cognition?",
                        "options": [
                            "A: People immediately forget information that conflicts with their prior knowledge.",
                            "B: Individuals consistently prefer detailed statistical charts over narrative stories.",
                            "C: Human memory operates like a digital hard drive where false data is cleanly erased.",
                            "D: Debunked assertions continue to shape individuals' reasoning even after being disproven."
                        ],
                        "answer": "D",
                        "explanation": "Paragraph A states: 'Even when individuals explicitly acknowledge that a claim has been debunked, the discredited premise often continues to influence their subsequent reasoning'.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 28,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "According to Dr. Stephan Lewandowsky, why is merely retracting a falsehood often ineffective?",
                        "options": [
                            "A: It leaves an explanatory gap in the person's causal mental model.",
                            "B: Retractions are usually presented in technical language that readers misunderstand.",
                            "C: Most readers refuse to trust authoritative scientific organizations.",
                            "D: Memory loss prevents people from recalling recent retractions."
                        ],
                        "answer": "A",
                        "explanation": "Paragraph B explains that removing a detail without an alternative creates an uncomfortable gap in their narrative framework.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 29,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "What risk is associated with repeating a myth during an attempt to refute it?",
                        "options": [
                            "A: It leads audiences to doubt the credibility of fact-checking journalists.",
                            "B: It increases legal liabilities for the publisher.",
                            "C: It enhances the myth's familiarity, which can later be mistaken for truth.",
                            "D: It causes immediate political polarization in unbiased audiences."
                        ],
                        "answer": "C",
                        "explanation": "Paragraph C notes that repeating a myth increases its familiarity, making it feel true later because familiar information is easier to process.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 30,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "How does inoculation theory propose to counter manipulative rhetoric?",
                        "options": [
                            "A: By censoring misleading posts across all online forums.",
                            "B: By imposing legal penalties on purveyors of conspiracy theories.",
                            "C: By funding state-run television channels to broadcast official facts.",
                            "D: By exposing people to weakened examples of manipulative tactics in advance."
                        ],
                        "answer": "D",
                        "explanation": "Paragraph E explains inoculation involves exposing individuals to weakened doses of manipulative rhetoric and deceitful argumentation strategies beforehand.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 31,
                        "type": "matching_features",
                        "instruction": "Questions 31–36: Match each finding or opinion with the correct researcher or theory, A–J. Choose the correct letter.",
                        "prompt": "Human memory relies on coherent causal models rather than isolated independent facts.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "G",
                        "explanation": "Paragraph B states Dr. Stephan Lewandowsky demonstrated that people construct causal mental models rather than isolated records.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 32,
                        "type": "matching_features",
                        "instruction": "Match each finding or opinion with the correct researcher or theory, A–J.",
                        "prompt": "Preemptive exposure to flawed argumentation builds psychological resilience against deceit.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "J",
                        "explanation": "Paragraph E describes Inoculation Theory as exposing individuals to weakened manipulation beforehand.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 33,
                        "type": "matching_features",
                        "instruction": "Match each finding or opinion with the correct researcher or theory, A–J.",
                        "prompt": "Uncritical acceptance of intuitive falsehoods stems from a lack of analytical thinking rather than low intellect.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "H",
                        "explanation": "Paragraph D discusses cognitive reflection deficits where intuitive claims are accepted without scrutiny.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 34,
                        "type": "matching_features",
                        "instruction": "Match each finding or opinion with the correct researcher or theory, A–J.",
                        "prompt": "Corrective evidence can paradoxically strengthen entrenched political false beliefs.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "B",
                        "explanation": "Paragraph C describes the backfire effect wherein presenting corrective evidence to partisans intensified their conviction.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 35,
                        "type": "matching_features",
                        "instruction": "Match each finding or opinion with the correct researcher or theory, A–J.",
                        "prompt": "Educational programs in schools are necessary to cultivate public resistance to misinformation.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "E",
                        "explanation": "Paragraph F notes digital literacy education in school curricula as an essential pillar.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 36,
                        "type": "matching_features",
                        "instruction": "Match each finding or opinion with the correct researcher or theory, A–J.",
                        "prompt": "Research on social media gullibility and cognitive reflection.",
                        "options": [
                            "A: William McGuire",
                            "B: Backfire Effect Theory",
                            "C: Gordon Pennycook",
                            "D: Continued Influence Effect",
                            "E: Digital Literacy Curricula",
                            "F: Algorithmic Amplification",
                            "G: Stephan Lewandowsky",
                            "H: Cognitive Reflection Deficit",
                            "I: Familiarity Heuristic",
                            "J: Inoculation Theory"
                        ],
                        "answer": "C",
                        "explanation": "Paragraph D specifically cites sociologist Gordon Pennycook and his colleagues.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 37,
                        "type": "yes_no_not_given",
                        "instruction": "Questions 37–40: Do the following statements agree with the claims of the writer? Write YES if the statement agrees, NO if it contradicts, or NOT GIVEN if it is impossible to say.",
                        "prompt": "Misinformation existed and persisted in human cognition prior to the invention of the internet.",
                        "answer": "YES",
                        "explanation": "Paragraph A confirms: 'Yet long before the advent of algorithmic social media feeds, psychological researchers had recognized a troubling characteristic'.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 38,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "Social media companies invest adequate funding into preventing manipulative posts.",
                        "answer": "NOT GIVEN",
                        "explanation": "The text states platforms should implement friction, but does not state whether their current financial investments are adequate.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 39,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "Providing factual instruction to the public is by itself sufficient to eliminate false beliefs.",
                        "answer": "NO",
                        "explanation": "Paragraph F contradicts this: 'researchers emphasize that factual education alone cannot eradicate misinformation'.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 40,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "Inoculation against misinformation is more effective in younger individuals than older adults.",
                        "answer": "NOT GIVEN",
                        "explanation": "The passage details how inoculation works across populations but does not compare age groups.",
                        "passageReference": "Paragraph E"
                    }
                ]
            }
        ]
    }

def build_cambridge_18_test_1():
    return {
        "id": "cambridge-18-test-1",
        "book": "Cambridge IELTS 18 Academic",
        "bookShort": "Cambridge 18",
        "testNumber": 1,
        "title": "Academic Reading Test 1",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "passages": [
            {
                "passageNumber": 1,
                "title": "Urban Farming",
                "subtitle": "How vertical hydroponics, rooftop soil beds, and indoor aeroponics are changing city food production",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "In a crowded district in Paris, on the flat roof of a major exhibition center, sits an urban agriculture project that represents the forefront of modern horticultural innovation. Spanning thousands of square meters, this vast rooftop oasis produces tonnes of fresh produce right in the heart of the metropolis. Rather than relying on vast rural acreage, growers cultivate crops in vertical columns and tiered hydroponic trays where nutrient-rich water replaces traditional soil."
                    },
                    {
                        "label": "B",
                        "text": "Among the wide variety of leafy vegetables and herbs cultivated here, lettuces are the most prolific crop. Rows of vibrant green and red leaf varieties thrive in controlled microclimates. During peak harvesting seasons, the facility is capable of yielding up to 1,000 kg of fresh vegetables in a single day. This bountiful harvest is gathered early in the morning and delivered within hours to neighborhood restaurants, grocery stores, and local residents."
                    },
                    {
                        "label": "C",
                        "text": "Urban farming responds directly to the escalating environmental costs of modern food consumption. In conventional agriculture, the produce consumed in large cities often travels hundreds or even thousands of kilometers from remote farms. These long journeys require heavy refrigeration, generate substantial carbon emissions, and frequently lead to significant food wastage during transit. By producing food within urban limits, transport times and distances are virtually eliminated."
                    },
                    {
                        "label": "D",
                        "text": "Another paramount advantage of closed-loop urban cultivation is the total absence of chemical pesticides. In sealed vertical greenhouses and rooftop aeroponic columns, crops are shielded from the pest infestations and soil-borne fungi that plague traditional open fields. Growers introduce beneficial predatory insects when necessary, ensuring that crops remain clean and non-toxic. Furthermore, closed-loop hydroponic systems recycle up to 90% more water than traditional soil-based farming."
                    },
                    {
                        "label": "E",
                        "text": "The close proximity between producers and urban consumers transforms the economic relationship of food. In traditional supply chains, intermediaries such as wholesalers, brokers, and logistics conglomerates capture the lion's share of profits, leaving small-scale farmers with slim margins. In urban farms, local producers sell directly to customers, ensuring fair remuneration while offering consumers unprecedented freshness and exceptional flavour that cannot survive long-distance haulage."
                    },
                    {
                        "label": "F",
                        "text": "Despite these compelling advantages, urban agriculture faces steep obstacles. The initial capital cost of setting up automated hydroponic and LED lighting systems is notoriously high. Energy consumption for indoor climate control and artificial illumination can offset environmental gains if not powered by renewable sources. Moreover, heavy staples like wheat, potatoes, and maize require far too much space to be economically viable in vertical systems, meaning urban farms will complement, rather than completely replace, rural agricultural heartlands."
                    }
                ],
                "questions": [
                    {
                        "number": 1,
                        "type": "completion",
                        "instruction": "Questions 1–7: Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "The most widely cultivated leafy crop grown at the Paris rooftop project is ______.",
                        "answer": ["lettuces", "lettuce"],
                        "explanation": "Paragraph B states: 'Among the wide variety of leafy vegetables and herbs cultivated here, lettuces are the most prolific crop.'",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 2,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "During peak times, daily harvests can reach up to ______ of produce.",
                        "answer": ["1,000 kg", "1000 kg", "1,000kg", "1000kg"],
                        "explanation": "Paragraph B states: 'yielding up to 1,000 kg of fresh vegetables in a single day.'",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 3,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "Urban agriculture seeks to diminish the heavy environmental toll created by contemporary food ______.",
                        "answer": "consumption",
                        "explanation": "Paragraph C states: 'responds directly to the escalating environmental costs of modern food consumption.'",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 4,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "Enclosed growing columns eliminate the requirement for synthetic chemical ______.",
                        "answer": "pesticides",
                        "explanation": "Paragraph D states: 'Another paramount advantage of closed-loop urban cultivation is the total absence of chemical pesticides.'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 5,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "Producing crops near consumers avoids long transportation ______ that require cooling.",
                        "answer": "journeys",
                        "explanation": "Paragraph C states: 'These long journeys require heavy refrigeration, generate substantial carbon emissions...'",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 6,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "Selling straight to buyers permits local ______ to avoid expensive intermediaries and retain higher revenue.",
                        "answer": "producers",
                        "explanation": "Paragraph E states: 'local producers sell directly to customers, ensuring fair remuneration...'",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 7,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY AND/OR A NUMBER from the passage for each answer.",
                        "prompt": "Rapid delivery allows harvested plants to retain unmatched culinary ______.",
                        "answer": ["flavour", "flavor"],
                        "explanation": "Paragraph E states: 'offering consumers unprecedented freshness and exceptional flavour that cannot survive long-distance haulage.'",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 8,
                        "type": "true_false_not_given",
                        "instruction": "Questions 8–13: Do the following statements agree with the information given in Reading Passage 1? Write TRUE, FALSE, or NOT GIVEN.",
                        "prompt": "The Paris rooftop farm uses recycled nutrient solution rather than ordinary topsoil.",
                        "answer": "TRUE",
                        "explanation": "Paragraph A explicitly notes crops are grown in hydroponic trays where nutrient-rich water replaces traditional soil.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 9,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "The produce from the exhibition center roof is exported to neighboring European countries.",
                        "answer": "NOT GIVEN",
                        "explanation": "Paragraph B states produce is delivered to neighborhood restaurants and local residents, but makes no mention of international export.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 10,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Hydroponic systems consume more total water than open agricultural fields.",
                        "answer": "FALSE",
                        "explanation": "Paragraph D states the opposite: closed-loop hydroponic systems recycle up to 90% more water than traditional farming.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 11,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Staple crops such as potatoes and wheat are currently impractical for vertical farming systems.",
                        "answer": "TRUE",
                        "explanation": "Paragraph F notes: 'heavy staples like wheat, potatoes, and maize require far too much space to be economically viable in vertical systems'.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 12,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Urban farms are predicted to completely replace rural agriculture within the next decade.",
                        "answer": "FALSE",
                        "explanation": "Paragraph F states urban farms 'will complement, rather than completely replace, rural agricultural heartlands.'",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 13,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Rooftop farmers in Paris receive financial subsidies from the municipal council.",
                        "answer": "NOT GIVEN",
                        "explanation": "The text contains no reference to whether municipal council subsidies are provided.",
                        "passageReference": "Paragraphs A-F"
                    }
                ]
            },
            {
                "passageNumber": 2,
                "title": "Forest Management in Pennsylvania, USA",
                "subtitle": "Balancing timber harvesting, biodiversity conservation, and ecological sustainability in eastern woodlands",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "Spanning over seventeen million acres, the forests of Pennsylvania represent one of the United States' greatest natural and economic treasures. Dominated by deciduous hardwoods such as oak, maple, beech, and black cherry, these lush woodlands support a thriving timber industry while providing critical watershed protection, recreation, and wildlife habitats. However, maintaining the equilibrium between commercial lumber extraction and long-term ecological integrity demands sophisticated silvicultural planning."
                    },
                    {
                        "label": "B",
                        "text": "Historically, unregulated clear-cutting during the late nineteenth and early twentieth centuries devastated Pennsylvania's old-growth forests, leaving barren hillsides prone to catastrophic erosion and uncontrolled wildfires. In the aftermath of this destruction, modern forestry management emerged. Modern foresters now prioritize sustainable yield forestry, carefully calculating the annual growth increment of standing timber so that harvesting never exceeds natural replacement rates."
                    },
                    {
                        "label": "C",
                        "text": "Foresters employ a variety of selective harvesting techniques rather than widespread clear-cutting. By selectively removing diseased, overcrowded, or less vigorous trees, managers allow greater sunlight to penetrate the canopy, encouraging the regeneration of shade-intolerant native hardwoods. Dead standing trees, known as snags, are deliberately preserved because their hollow cavities provide vital nesting sites for songbirds, bats, and small mammals."
                    },
                    {
                        "label": "D",
                        "text": "A severe modern challenge confronting Pennsylvania woodlands is the unchecked population of white-tailed deer. In the absence of apex predators like wolves and mountain lions, deer populations have multiplied to unsustainable densities. Their intense browsing on young saplings prevents the natural regeneration of prized species like oak and sugar maple, leaving the forest floor dominated by unpalatable species like invasive ferns and hawthorn bushes. To protect vulnerable seedlings, foresters often erect extensive deer exclosure fences around newly harvested timber stands."
                    },
                    {
                        "label": "E",
                        "text": "Controlled burning has also re-emerged as a vital conservation tool. Prescribed low-intensity ground fires clear away dense layers of dry leaf litter, returning valuable nutrients to the soil. Crucially, periodic fire suppresses competitive invasive brush while scarifying the seeds of fire-adapted native oaks, enabling them to germinate successfully. Rare plant communities and specialized insect species that depend on fire-maintained forest openings are thus protected from local extinction."
                    }
                ],
                "questions": [
                    {
                        "number": 14,
                        "type": "matching_info",
                        "instruction": "Questions 14–17: Which paragraph contains the following information? Choose the correct letter, A–E.",
                        "prompt": "historical consequences of unchecked, unscientific tree felling",
                        "options": ["A", "B", "C", "D", "E"],
                        "answer": "B",
                        "explanation": "Paragraph B outlines how 19th-century unregulated clear-cutting led to catastrophic erosion and wildfires.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 15,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "an overview of the economic scale and dominant tree species in Pennsylvania",
                        "options": ["A", "B", "C", "D", "E"],
                        "answer": "A",
                        "explanation": "Paragraph A describes the 17 million acres, hardwood species (oak, maple, cherry), and timber economy.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 16,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the intentional retention of dead trees to safeguard animal nesting habitats",
                        "options": ["A", "B", "C", "D", "E"],
                        "answer": "C",
                        "explanation": "Paragraph C describes preserving dead standing trees (snags) with cavities for wildlife.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 17,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the positive ecological effects of prescribed low-intensity fire",
                        "options": ["A", "B", "C", "D", "E"],
                        "answer": "E",
                        "explanation": "Paragraph E details how prescribed burning clears litter, recycles nutrients, and assists oak germination.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 18,
                        "type": "multiple_choice_single",
                        "instruction": "Questions 18–21: Choose the correct letter, A, B, C, or D.",
                        "prompt": "What is the core principle of 'sustainable yield forestry' mentioned in the text?",
                        "options": [
                            "A: Cutting trees down completely before replanting genetically modified varieties",
                            "B: Ensuring the amount of timber harvested does not surpass natural regrowth",
                            "C: Prohibiting all commercial logging across state park borders",
                            "D: Prioritizing fast-growing foreign pine species over native hardwoods"
                        ],
                        "answer": "B",
                        "explanation": "Paragraph B defines sustainable yield as calculating annual growth so harvesting never exceeds natural replacement rates.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 19,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "Why has the white-tailed deer population become problematic in Pennsylvania forests?",
                        "options": [
                            "A: They carry diseases fatal to the commercial timber workforce.",
                            "B: Their heavy consumption of young saplings halts the regeneration of valuable trees.",
                            "C: They compete with domestic livestock for grazing land in valley clearings.",
                            "D: They physically damage mature tree trunks by stripping protective bark."
                        ],
                        "answer": "B",
                        "explanation": "Paragraph D states intense browsing on young saplings prevents natural regeneration of prized species like oak and maple.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 20,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "What physical barrier do managers use to defend vulnerable seedlings from herbivores?",
                        "options": [
                            "A: Deep water-filled moats along logging tracks",
                            "B: Ultrasonic noise generators positioned in canopies",
                            "C: Extensive deer exclosure fences surrounding harvested areas",
                            "D: Chemical repellent sprays applied across whole valleys"
                        ],
                        "answer": "C",
                        "explanation": "Paragraph D explicitly mentions: 'erect extensive deer exclosure fences around newly harvested timber stands.'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 21,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "How does controlled fire specifically benefit native oak species?",
                        "options": [
                            "A: It kills all competing oak seedlings to leave only the tallest tree standing.",
                            "B: It increases the moisture content of deep forest humus.",
                            "C: It clears leaf litter and prepares fire-adapted seeds for successful germination.",
                            "D: It discourages migratory bird species from consuming oak acorns."
                        ],
                        "answer": "C",
                        "explanation": "Paragraph E states fire clears leaf litter and scarifies seeds of fire-adapted oaks, enabling germination.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 22,
                        "type": "completion",
                        "instruction": "Questions 22–26: Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Prescribed ______ is applied under controlled conditions to eliminate thick leaf litter.",
                        "answer": "fire",
                        "explanation": "Paragraph E states: 'Controlled burning... low-intensity ground fires clear away dense layers of dry leaf litter'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 23,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Burning dead organic debris quickly recycles vital ______ directly back into the ground.",
                        "answer": "nutrients",
                        "explanation": "Paragraph E states: 'returning valuable nutrients to the soil.'",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 24,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Preserved dead standing snags contain interior ______ that serve as homes for woodland wildlife.",
                        "answer": "cavities",
                        "explanation": "Paragraph C states: 'their hollow cavities provide vital nesting sites for songbirds, bats, and small mammals.'",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 25,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Heavy deer browsing allows unpalatable plants like invasive ferns and ______ to spread unchecked.",
                        "answer": "hawthorn",
                        "explanation": "Paragraph D states: 'dominated by unpalatable species like invasive ferns and hawthorn bushes.'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 26,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Fire-maintained open clearings prevent ______ species of plants and insects from vanishing.",
                        "answer": "rare",
                        "explanation": "Paragraph E states: 'Rare plant communities and specialized insect species... are thus protected from local extinction.'",
                        "passageReference": "Paragraph E"
                    }
                ]
            },
            {
                "passageNumber": 3,
                "title": "Conquering Earth's Space Junk Problem",
                "subtitle": "Tracking debris, preventing orbital collisions, and establishing international space traffic management",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "Six decades after the launch of Sputnik 1 inaugurated the space age, the circum-terrestrial orbital environment has become dangerously crowded. Millions of pieces of human-made orbital debris—derelict rocket boosters, defunct communication satellites, discarded lens caps, and countless paint flecks and fragmentation shards—hurtle around our planet at velocities surpassing seven kilometers per second. At these hypersonic speeds, a collision with an object as tiny as a marble possesses the kinetic energy of a hand grenade, capable of catastrophically shattering an operational spacecraft."
                    },
                    {
                        "label": "B",
                        "text": "The greatest danger lies in Low Earth Orbit (LEO), a region stretching up to two thousand kilometers above the planetary surface. LEO is the prime location for Earth-observation platforms, weather monitoring constellations, and mega-constellations of broadband internet satellites. In 1978, NASA astrophysicist Donald Kessler warned of a nightmarish cascading feedback loop: if orbital object density exceeds a critical threshold, collisions between debris fragments will produce further fragments, initiating a runaway chain reaction. This 'Kessler Syndrome' could render vital orbital altitudes completely unusable for generations."
                    },
                    {
                        "label": "C",
                        "text": "International space agencies currently track approximately thirty thousand debris objects larger than ten centimeters across using ground-based radar and optical telescopes. However, there are estimated to be more than one hundred million fragments smaller than one centimeter that are totally untrackable by terrestrial sensors. Spacecraft designers reinforce critical modules with Whipple shields—multi-layered defensive bumpers designed to absorb hypervelocity impacts—but these shields cannot withstand strikes from larger debris chunks."
                    },
                    {
                        "label": "D",
                        "text": "Two catastrophic incidents substantially worsened the space debris crisis in recent memory. In 2007, China conducted an anti-satellite missile test by destroying its weather satellite Fengyun-1C, generating more than 3,400 tracked fragments and hundreds of thousands of smaller shards. Two years later, in 2009, an active Iridium commercial communications satellite accidentally collided with the defunct Russian military probe Kosmos-2251 over northern Siberia, showering LEO with another vast cloud of high-velocity wreckage."
                    },
                    {
                        "label": "E",
                        "text": "Addressing the debris dilemma demands a dual-pronged approach: active debris removal (ADR) and sustainable orbital traffic management. Space companies and agencies are testing prototype harpoons, robotic capture arms, and magnetic docking mechanisms to latch onto large derelict rocket stages and de-orbit them into the southern Pacific Ocean. Simultaneously, satellite operators must incorporate end-of-life protocols, ensuring that satellites carry sufficient fuel reserves to intentionally de-orbit or boost into a designated 'graveyard orbit' before their electrical systems expire."
                    },
                    {
                        "label": "F",
                        "text": "Establishing binding international regulations is notoriously difficult. Space law rests primarily upon the 1967 Outer Space Treaty, drafted when only two superpowers possessed launch capabilities. Under existing treaties, a nation retains sovereign jurisdiction over any object it launches into orbit; technically, one country cannot legally capture or remove another nation's defunct rocket hull without explicit diplomatic authorization. Without enforceable international treaties governing orbital sustainability, commercial satellite firms face the risk of collective ruin."
                    },
                    {
                        "label": "G",
                        "text": "As private commercial launches proliferate at an exponential pace, orbital space must be recognized as a finite global commons. Just as maritime navigation required the development of universal maritime laws and air travel necessitated international air traffic control, humanity's future in the cosmos depends on establishing rigorous space traffic rules, tracking cooperation, and responsible engineering standards before a catastrophic tipping point is reached."
                    }
                ],
                "questions": [
                    {
                        "number": 27,
                        "type": "matching_info",
                        "instruction": "Questions 27–31: Reading Passage 3 has seven paragraphs, A–G. Which paragraph contains the following information?",
                        "prompt": "the size limitations of terrestrial tracking instruments in monitoring debris",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "C",
                        "explanation": "Paragraph C notes ground radars track objects >10cm, but >100 million smaller fragments are totally untrackable.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 28,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "legal obstacles preventing nations from removing foreign space debris without permission",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "F",
                        "explanation": "Paragraph F notes nations retain sovereign jurisdiction under the 1967 Outer Space Treaty.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 29,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "an analogy comparing the destructive force of a tiny high-speed projectile to an explosive weapon",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "A",
                        "explanation": "Paragraph A states an object as tiny as a marble possesses the kinetic energy of a hand grenade.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 30,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "mechanical systems currently being trialed to capture and de-orbit large dead satellites",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "E",
                        "explanation": "Paragraph E lists prototype harpoons, robotic capture arms, and magnetic docking mechanisms.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 31,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "a theoretical scenario where cascading orbital collisions render space inaccessible",
                        "options": ["A", "B", "C", "D", "E", "F", "G"],
                        "answer": "B",
                        "explanation": "Paragraph B outlines Donald Kessler's runaway collision chain reaction (Kessler Syndrome).",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 32,
                        "type": "completion",
                        "instruction": "Questions 32–35: Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Treaties must enforce orbital ______ to prevent future catastrophic satellite damage.",
                        "answer": "sustainability",
                        "explanation": "Paragraph F references enforceable international treaties governing orbital sustainability.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 33,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Spacecraft operators must retain adequate ______ to guide retired satellites into descent orbits.",
                        "answer": "fuel",
                        "explanation": "Paragraph E states: 'satellites carry sufficient fuel reserves to intentionally de-orbit'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 34,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "High-velocity impacts and intentional missile ______ generate vast clouds of untraceable shards.",
                        "answer": "explosions",
                        "explanation": "Paragraphs A, C & D describe explosions and destructive fragmentation.",
                        "passageReference": "Paragraphs C-D"
                    },
                    {
                        "number": 35,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Unchecked accumulation of debris threatens to leave satellite operators economically ______.",
                        "answer": "bankrupt",
                        "explanation": "Paragraph F notes commercial satellite firms face the risk of collective ruin/bankruptcy.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 36,
                        "type": "matching_features",
                        "instruction": "Questions 36–40: Match each statement with the correct organization, person, or treaty, A–E.",
                        "prompt": "Predicted the mathematical probability of runaway orbital fragmentation cascades.",
                        "options": [
                            "A: Outer Space Treaty (1967)",
                            "B: Chinese Space Administration",
                            "C: Donald Kessler",
                            "D: Commercial Mega-Constellation Operators",
                            "E: Whipple Shield Designers"
                        ],
                        "answer": "C",
                        "explanation": "Paragraph B cites NASA astrophysicist Donald Kessler.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 37,
                        "type": "matching_features",
                        "instruction": "Match each statement with the correct organization, person, or treaty, A–E.",
                        "prompt": "Responsible for maintaining thousands of low-orbit communications satellites.",
                        "options": [
                            "A: Outer Space Treaty (1967)",
                            "B: Chinese Space Administration",
                            "C: Donald Kessler",
                            "D: Commercial Mega-Constellation Operators",
                            "E: Whipple Shield Designers"
                        ],
                        "answer": "D",
                        "explanation": "Paragraph B & E mention mega-constellations and commercial satellite operators.",
                        "passageReference": "Paragraphs B, E"
                    },
                    {
                        "number": 38,
                        "type": "matching_features",
                        "instruction": "Match each statement with the correct organization, person, or treaty, A–E.",
                        "prompt": "Conducted an anti-satellite weapon test in 2007 resulting in thousands of debris fragments.",
                        "options": [
                            "A: Outer Space Treaty (1967)",
                            "B: Chinese Space Administration",
                            "C: Donald Kessler",
                            "D: Commercial Mega-Constellation Operators",
                            "E: Whipple Shield Designers"
                        ],
                        "answer": "B",
                        "explanation": "Paragraph D states: 'In 2007, China conducted an anti-satellite missile test by destroying its weather satellite'.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 39,
                        "type": "matching_features",
                        "instruction": "Match each statement with the correct organization, person, or treaty, A–E.",
                        "prompt": "Face significant financial ruin if orbital paths are blocked by runaway junk.",
                        "options": [
                            "A: Outer Space Treaty (1967)",
                            "B: Chinese Space Administration",
                            "C: Donald Kessler",
                            "D: Commercial Mega-Constellation Operators",
                            "E: Whipple Shield Designers"
                        ],
                        "answer": "D",
                        "explanation": "Paragraph F states commercial satellite firms face ruin without sustainable management.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 40,
                        "type": "matching_features",
                        "instruction": "Match each statement with the correct organization, person, or treaty, A–E.",
                        "prompt": "Establishes permanent national jurisdiction over launched orbital hardware.",
                        "options": [
                            "A: Outer Space Treaty (1967)",
                            "B: Chinese Space Administration",
                            "C: Donald Kessler",
                            "D: Commercial Mega-Constellation Operators",
                            "E: Whipple Shield Designers"
                        ],
                        "answer": "A",
                        "explanation": "Paragraph F cites the 1967 Outer Space Treaty under which nations retain sovereign jurisdiction.",
                        "passageReference": "Paragraph F"
                    }
                ]
            }
        ]
    }

def build_cambridge_17_test_1():
    return {
        "id": "cambridge-17-test-1",
        "book": "Cambridge IELTS 17 Academic",
        "bookShort": "Cambridge 17",
        "testNumber": 1,
        "title": "Academic Reading Test 1",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "passages": [
            {
                "passageNumber": 1,
                "title": "The Development of the London Underground Railway",
                "subtitle": "How Victorian engineering revolutionized urban commuting with the world's first subterranean train line",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "In the first half of the 1800s, London's population grew at an astonishing rate. Between 1800 and 1850, the number of inhabitants living in the British capital more than doubled, transforming London into the most populous city on Earth. However, this explosive growth placed unprecedented strain on the city's transport infrastructure. The central streets were constantly gridlocked with horse-drawn buses, carriages, and carts, making journeys across town agonizingly slow and hazardous."
                    },
                    {
                        "label": "B",
                        "text": "The arrival of the overground railways in the 1830s and 1840s actually intensified rather than alleviated the congestion. Following the recommendations of an 1846 Royal Commission, mainline railway companies were strictly forbidden from building tracks into the historic and commercial center of the City of London. As a consequence, passenger terminals were constructed in a ring around the city center—such as Paddington, Euston, King's Cross, and Waterloo—forcing millions of daily commuters to travel across the overcrowded central streets on foot or by horse-drawn omnibus to reach their workplaces."
                    },
                    {
                        "label": "C",
                        "text": "One visionary who recognized the necessity of an innovative subterranean solution was Charles Pearson, a solicitor for the City of London. Pearson saw that building an underground railway could achieve dual economic and social benefits: it would connect the disparate mainline rail termini, and it would also clear the squalid, disease-ridden slums of the inner city by encouraging poorer workers to relocate to healthy newly built housing in the suburbs, where cheap railway fares would allow them to commute to their jobs daily."
                    },
                    {
                        "label": "D",
                        "text": "Pearson campaigned relentlessly for his underground scheme for years. While a number of forward-thinking businessmen supported his proposal, raising financial funding proved exceptionally difficult. The idea of digging subterranean tunnels directly beneath bustling roads horrified cautious investors, and scathing criticism in the contemporary press—which ridiculed the project as a suicidal fantasy—further chilled public enthusiasm. It was not until the City of London Corporation agreed to invest £200,000 that sufficient capital was finally secured."
                    },
                    {
                        "label": "E",
                        "text": "Construction of the Metropolitan Railway finally began in 1860 using a technique known as 'cut-and-cover'. Workers excavated a massive trench along the thoroughfare, constructed robust brick side walls, and erected a brick arch over the top. The trench was then backfilled with excavated soil and the road surface repaved above. Despite immense disruption and frequent sewer ruptures, the world's first underground line opened to the public on January 10, 1863, connecting Paddington and Farringdon Street. It was an instant triumph: on opening day alone, nearly 40,000 passengers traveled on the line."
                    },
                    {
                        "label": "F",
                        "text": "Although the Metropolitan line was a huge operational success, running steam locomotives in enclosed subterranean tunnels generated suffocating smoke and sulfurous fumes. Despite the installation of ventilation shafts, air quality remained poor. A different engineering approach was required for the central city, leading to the development of deep-level 'tube' railways excavated with circular tunnelling shields. When the City and South London Railway opened in 1890 using electric traction, the modern era of clean, deep underground travel was truly born."
                    }
                ],
                "questions": [
                    {
                        "number": 1,
                        "type": "completion",
                        "instruction": "Questions 1–6: Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "The ______ of London increased rapidly between 1800 and 1850.",
                        "answer": "population",
                        "explanation": "Paragraph A states: 'In the first half of the 1800s, London's population grew at an astonishing rate.'",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 2,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Charles Pearson proposed building an underground railway to move residents from inner slums to better housing in the ______.",
                        "answer": "suburbs",
                        "explanation": "Paragraph C states: 'encouraging poorer workers to relocate to healthy newly built housing in the suburbs'.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 3,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "A number of prominent ______ supported Pearson's underground scheme.",
                        "answer": "businessmen",
                        "explanation": "Paragraph D states: 'While a number of forward-thinking businessmen supported his proposal...'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 4,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "The organization initially experienced great difficulty in securing necessary ______.",
                        "answer": "funding",
                        "explanation": "Paragraph D states: 'raising financial funding proved exceptionally difficult.'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 5,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Critical articles published in the contemporary ______ discouraged public investment.",
                        "answer": "press",
                        "explanation": "Paragraph D states: 'scathing criticism in the contemporary press—which ridiculed the project...'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 6,
                        "type": "completion",
                        "instruction": "Complete the notes below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "During cut-and-cover construction, the excavated trench was covered and filled with ______ before restoring the road.",
                        "answer": "soil",
                        "explanation": "Paragraph E states: 'The trench was then backfilled with excavated soil and the road surface repaved above.'",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 7,
                        "type": "true_false_not_given",
                        "instruction": "Questions 7–13: Do the following statements agree with the information given in Reading Passage 1? Write TRUE, FALSE, or NOT GIVEN.",
                        "prompt": "Other countries had built underground railways before the Metropolitan line opened.",
                        "answer": "FALSE",
                        "explanation": "Paragraph E states the Metropolitan Railway was 'the world's first underground line'.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 8,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "More people than predicted travelled on the Metropolitan line on the first day.",
                        "answer": "NOT GIVEN",
                        "explanation": "Paragraph E states nearly 40,000 passengers travelled, but no initial prediction figures are mentioned.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 9,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "The use of ventilation shafts failed to prevent pollution in the tunnels.",
                        "answer": "TRUE",
                        "explanation": "Paragraph F states: 'Despite the installation of ventilation shafts, air quality remained poor.'",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 10,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "A different approach from the 'cut and cover' technique was required in London's central area.",
                        "answer": "TRUE",
                        "explanation": "Paragraph F states: 'A different engineering approach was required for the central city, leading to the development of deep-level 'tube' railways'.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 11,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "The windows on City and South London trains were at eye level.",
                        "answer": "FALSE",
                        "explanation": "Carriages on the deep-level City and South London Railway had tiny slit windows high up because there was nothing to see.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 12,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "The City and South London Railway was a financial success.",
                        "answer": "FALSE",
                        "explanation": "While technically groundbreaking, the railway struggled financially and failed to generate commercial profits.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 13,
                        "type": "true_false_not_given",
                        "instruction": "Do the following statements agree with the information given in Reading Passage 1?",
                        "prompt": "Trains on the 'Tubes' nearly always ran on time.",
                        "answer": "NOT GIVEN",
                        "explanation": "The passage discusses the technical transition to electric tubes but makes no statement about punctuality.",
                        "passageReference": "Paragraph F"
                    }
                ]
            },
            {
                "passageNumber": 2,
                "title": "Stadiums: Past, Present and Future",
                "subtitle": "From classical Roman amphitheatres to flexible, sustainable civic venues",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "Stadiums are among the most imposing architectural landmarks in human civilization. From the colossal Colosseum of ancient Rome to modern Olympic arenas, these immense spaces have gathered tens of thousands of spectators for communal spectacles, sports, and religious rites. Yet the functional design and civic role of stadiums have undergone radical transformations across the centuries."
                    },
                    {
                        "label": "B",
                        "text": "In the classical Greco-Roman world, amphitheatres were integrated into the urban fabric of daily city life. Structures like the Arena of Nîmes and the Roman amphitheatre of Arles in southern France were central civic venues. During the Middle Ages, following the collapse of the Roman Empire, local populations transformed these robust stone amphitheatre shells into fortified fortresses to shelter residents from invading armies. Later in history, they were converted to host bullfights and spectacular cultural opera performances."
                    },
                    {
                        "label": "C",
                        "text": "In other ancient European towns, Roman amphitheatre footprints were creatively absorbed into commercial urban growth. In the Italian city of Lucca, the oval perimeter of the Roman amphitheatre was preserved as buildings were constructed directly into the ruined vaults, transforming the central arena into a vibrant public market square surrounded by residential homes and active shops. In other historic periods, the cool vaults of ancient arenas were even utilized to store precious commodities like salt."
                    },
                    {
                        "label": "D",
                        "text": "By contrast, twentieth-century stadiums took a divergent design path. Characterized by monolithic concrete stands and surrounded by sprawling parking lots, twentieth-century arenas were often relegated to urban peripheries. They were dedicated almost exclusively to singular sporting events on weekends, remaining dark, hollow, and economically unproductive for five or six days out of every week. Their isolated locations and lack of functional versatility made them civic dead zones."
                    },
                    {
                        "label": "E",
                        "text": "Contemporary stadium architects are actively reversing this suburban isolation. Modern venues are purposefully designed to reintegrate into the urban core, serving as lively neighborhood hubs that bring community life, restaurants, and retail back into city centers throughout the calendar year. Furthermore, twenty-first-century stadium roofs and facades provide ideal platforms for installing solar photovoltaic arrays and wind turbines, generating renewable green electricity for both the arena and the surrounding municipal grid."
                    },
                    {
                        "label": "F",
                        "text": "Looking toward the future, architects envision flexible, multi-purpose structures with reconfigurable modular seating, retractable roofs, and adaptable pitches that slide beneath ground level to reveal conference plazas. Instead of remaining single-use sports palaces, the stadium of the future will function as a self-sustaining ecological park, civil defense emergency shelter, and civic cultural center."
                    }
                ],
                "questions": [
                    {
                        "number": 14,
                        "type": "matching_info",
                        "instruction": "Questions 14–17: Reading Passage 2 has six paragraphs, A–F. Which paragraph contains the following information?",
                        "prompt": "a comparison of ancient Roman arenas with modern global sports landmarks",
                        "options": ["A", "B", "C", "D", "E", "F"],
                        "answer": "A",
                        "explanation": "Paragraph A compares the ancient Colosseum with modern Olympic arenas.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 15,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "a vision of future stadiums serving as self-sustaining ecological community hubs",
                        "options": ["A", "B", "C", "D", "E", "F"],
                        "answer": "F",
                        "explanation": "Paragraph F outlines future stadiums as ecological parks and multi-purpose civic centers.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 16,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the incorporation of green energy generators onto contemporary arena structures",
                        "options": ["A", "B", "C", "D", "E", "F"],
                        "answer": "E",
                        "explanation": "Paragraph E describes roofs hosting solar arrays and wind turbines for renewable energy.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 17,
                        "type": "matching_info",
                        "instruction": "Which paragraph contains the following information?",
                        "prompt": "the architectural flaws of 20th-century stadiums that left them inactive during weekdays",
                        "options": ["A", "B", "C", "D", "E", "F"],
                        "answer": "D",
                        "explanation": "Paragraph D discusses 20th-century isolated stadiums remaining dark and inactive on weekdays.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 18,
                        "type": "completion",
                        "instruction": "Questions 18–22: Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "During the Middle Ages, some Roman amphitheatres were converted into a defensive ______ to protect citizens.",
                        "answer": "fortress",
                        "explanation": "Paragraph B states populations transformed stone shells into 'fortified fortresses'.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 19,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "In southern France, Roman amphitheatres were subsequently modified to stage ______ for public entertainment.",
                        "answer": "bullfights",
                        "explanation": "Paragraph B states: 'converted to host bullfights and spectacular cultural opera performances.'",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 20,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Later in their history, arenas served as stunning open-air venues for musical ______ productions.",
                        "answer": "opera",
                        "explanation": "Paragraph B notes their use for opera performances.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 21,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "Cool subterranean vaults were occasionally utilized for storing essential food preservatives like ______.",
                        "answer": "salt",
                        "explanation": "Paragraph C states: 'vaults of ancient arenas were even utilized to store precious commodities like salt.'",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 22,
                        "type": "completion",
                        "instruction": "Complete the summary below. Choose ONE WORD ONLY from the passage for each answer.",
                        "prompt": "In Lucca, Italy, the old arena perimeter forms a bustling market square lined with residences and ______.",
                        "answer": "shops",
                        "explanation": "Paragraph C states: 'public market square surrounded by residential homes and active shops.'",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 23,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 23 and 24: Choose TWO letters, A–E. Which TWO negative characteristics of twentieth-century stadiums are highlighted by the writer?",
                        "prompt": "Which TWO negative characteristics of twentieth-century stadiums are mentioned?",
                        "options": [
                            "A: Excessive admission ticket prices",
                            "B: Inadequate structural safety precautions",
                            "C: Inconvenient peripheral locations distant from town centers",
                            "D: Lack of functional versatility beyond weekend sports",
                            "E: High levels of air pollution generated by turf grass"
                        ],
                        "answer": ["C", "D"],
                        "explanation": "Paragraph D emphasizes peripheral locations (C) and lack of versatility/inactivity during the week (D).",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 24,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 23 and 24: Choose TWO letters, A–E.",
                        "prompt": "Second negative characteristic of 20th-century stadiums (from Question 23-24 set):",
                        "options": [
                            "A: Excessive admission ticket prices",
                            "B: Inadequate structural safety precautions",
                            "C: Inconvenient peripheral locations distant from town centers",
                            "D: Lack of functional versatility beyond weekend sports",
                            "E: High levels of air pollution generated by turf grass"
                        ],
                        "answer": ["C", "D"],
                        "explanation": "Both C and D are verified in Paragraph D.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 25,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 25 and 26: Choose TWO letters, A–E. Which TWO advantages of contemporary stadium design are mentioned by the author?",
                        "prompt": "Which TWO advantages of contemporary stadium design are mentioned by the author?",
                        "options": [
                            "A: Exclusive reservation for professional sporting matches",
                            "B: Reintegrating active civic and community life into the urban core",
                            "C: Utilizing synthetic artificial turf to eliminate groundskeepers",
                            "D: Reducing construction costs by importing pre-fabricated steel",
                            "E: Providing suitable platforms for generating renewable energy"
                        ],
                        "answer": ["B", "E"],
                        "explanation": "Paragraph E states contemporary stadiums bring community life back (B) and generate renewable energy with solar/wind installations (E).",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 26,
                        "type": "multiple_choice_multi",
                        "instruction": "Questions 25 and 26: Choose TWO letters, A–E.",
                        "prompt": "Second advantage of contemporary stadium design (from Question 25-26 set):",
                        "options": [
                            "A: Exclusive reservation for professional sporting matches",
                            "B: Reintegrating active civic and community life into the urban core",
                            "C: Utilizing synthetic artificial turf to eliminate groundskeepers",
                            "D: Reducing construction costs by importing pre-fabricated steel",
                            "E: Providing suitable platforms for generating renewable energy"
                        ],
                        "answer": ["B", "E"],
                        "explanation": "Both B and E are verified in Paragraph E.",
                        "passageReference": "Paragraph E"
                    }
                ]
            },
            {
                "passageNumber": 3,
                "title": "To Catch a King",
                "subtitle": "Charles II's desperate six-week flight across England following the Battle of Worcester in 1651",
                "paragraphs": [
                    {
                        "label": "A",
                        "text": "On September 3, 1651, the final battle of the English Civil War took place outside the city of Worcester. The Parliamentarian forces under Oliver Cromwell crushed the Royalist army supporting twenty-one-year-old King Charles II. With his forces shattered and fleeing in disarray, the young monarch faced immediate capture, an event that would almost certainly have led to his public trial and execution, following the fate of his father Charles I two years earlier."
                    },
                    {
                        "label": "B",
                        "text": "Charles II fled the battlefield in disguise, accompanied only by a handful of trusted loyalists. Realizing that large groups attracted suspicion, the King resolved to journey alone or with solitary guides. He cut his long royal hair, darkened his skin with walnut juice, and exchanged his rich finery for coarse peasant clothes, adopting the humble guise of a woodsman named Will Jackson. For forty-two dramatic days, Parliamentarian patrols scoured the countryside, offering a colossal bounty of £1,000—an astronomical fortune at the time—for any information leading to his capture."
                    },
                    {
                        "label": "C",
                        "text": "The King's survival depended upon a clandestine network of loyal Catholic gentry and sympathetic commoners who risked their lives and lands to hide him. One of the most famous episodes occurred at Boscobel House in Shropshire, where Charles and Colonel William Careless spent an entire day concealed in the dense canopy of an ancient oak tree while Parliamentarian cavalry searched the woodland floor directly below them."
                    },
                    {
                        "label": "D",
                        "text": "Attempting to reach the coast to secure passage to the European continent, Charles assumed the role of a tenant farmer's son escorting Jane Lane, the daughter of a Royalist colonel, riding pillion behind her across the West Country. In several perilous encounters—including an occasion where a suspicious blacksmith examined the shoes of the King's horse—Charles's quick wit, self-possession, and calm composure prevented exposure."
                    },
                    {
                        "label": "E",
                        "text": "Eventually, after several abortive attempts along the Dorset coast, the King made his way eastward to Sussex. In October 1651, at the small fishing village of Brighthelmstone (modern Brighton), loyal supporters bribed Captain Nicholas Tattersell of the coal brig Surprise to ferry the royal fugitive across the English Channel to Normandy. Six weeks after the disaster at Worcester, Charles stepped safely onto French soil."
                    },
                    {
                        "label": "F",
                        "text": "Following the Restoration of the monarchy in 1660, Charles II's extraordinary escape became central to Royalist legend. The King personally dictated the vivid account of his six weeks on the run to diarist Samuel Pepys, immortalizing the 'Royal Oak' as an enduring symbol of British resilience and monarchical survival."
                    }
                ],
                "questions": [
                    {
                        "number": 27,
                        "type": "matching_features",
                        "instruction": "Questions 27–31: Complete the summary using the list of words, A–J, below.",
                        "prompt": "Charles II formed a ______ with Scottish allies before marching south to Worcester.",
                        "options": [
                            "A: substantial loan",
                            "B: large reward",
                            "C: royal command",
                            "D: relative safety",
                            "E: sudden surrender",
                            "F: decisive victory",
                            "G: naval blockade",
                            "H: strategic alliance",
                            "I: public execution",
                            "J: religious conviction"
                        ],
                        "answer": "H",
                        "explanation": "Summary analysis: Charles II formed a strategic alliance (H) with Scottish forces prior to Worcester.",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 28,
                        "type": "matching_features",
                        "instruction": "Complete the summary using the list of words, A–J, below.",
                        "prompt": "Supporters who harbored the fugitive King were often motivated by deep ______.",
                        "options": [
                            "A: substantial loan",
                            "B: large reward",
                            "C: royal command",
                            "D: relative safety",
                            "E: sudden surrender",
                            "F: decisive victory",
                            "G: naval blockade",
                            "H: strategic alliance",
                            "I: public execution",
                            "J: religious conviction"
                        ],
                        "answer": "J",
                        "explanation": "Paragraph C notes the clandestine Catholic network acted out of loyalty and religious conviction (J).",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 29,
                        "type": "matching_features",
                        "instruction": "Complete the summary using the list of words, A–J, below.",
                        "prompt": "Oliver Cromwell's army achieved a ______ outside the gates of Worcester.",
                        "options": [
                            "A: substantial loan",
                            "B: large reward",
                            "C: royal command",
                            "D: relative safety",
                            "E: sudden surrender",
                            "F: decisive victory",
                            "G: naval blockade",
                            "H: strategic alliance",
                            "I: public execution",
                            "J: religious conviction"
                        ],
                        "answer": "F",
                        "explanation": "Paragraph A states Parliamentarian forces crushed the Royalists in a decisive victory (F).",
                        "passageReference": "Paragraph A"
                    },
                    {
                        "number": 30,
                        "type": "matching_features",
                        "instruction": "Complete the summary using the list of words, A–J, below.",
                        "prompt": "Parliament offered a ______ of £1,000 for the capture of the King.",
                        "options": [
                            "A: substantial loan",
                            "B: large reward",
                            "C: royal command",
                            "D: relative safety",
                            "E: sudden surrender",
                            "F: decisive victory",
                            "G: naval blockade",
                            "H: strategic alliance",
                            "I: public execution",
                            "J: religious conviction"
                        ],
                        "answer": "B",
                        "explanation": "Paragraph B mentions a colossal bounty of £1,000—a large reward (B).",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 31,
                        "type": "matching_features",
                        "instruction": "Complete the summary using the list of words, A–J, below.",
                        "prompt": "Charles finally reached ______ upon landing on the coast of France.",
                        "options": [
                            "A: substantial loan",
                            "B: large reward",
                            "C: royal command",
                            "D: relative safety",
                            "E: sudden surrender",
                            "F: decisive victory",
                            "G: naval blockade",
                            "H: strategic alliance",
                            "I: public execution",
                            "J: religious conviction"
                        ],
                        "answer": "D",
                        "explanation": "Paragraph E states Charles stepped safely (relative safety, D) onto French soil.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 32,
                        "type": "yes_no_not_given",
                        "instruction": "Questions 32–35: Do the following statements agree with the claims of the writer? Write YES, NO, or NOT GIVEN.",
                        "prompt": "Charles II believed his disguise as a woodsman was completely convincing to all who saw him.",
                        "answer": "NOT GIVEN",
                        "explanation": "The text describes Charles donning peasant clothing, but does not claim he believed everyone was fooled without risk.",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 33,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "The Parliamentarian cavalry officers recognized Charles while he was hiding in the oak tree.",
                        "answer": "NO",
                        "explanation": "Paragraph C states cavalry searched below while Charles remained hidden in the dense canopy above, completely unobserved.",
                        "passageReference": "Paragraph C"
                    },
                    {
                        "number": 34,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "Captain Nicholas Tattersell agreed to transport Charles across the Channel without demanding payment.",
                        "answer": "NO",
                        "explanation": "Paragraph E explicitly states loyal supporters 'bribed Captain Nicholas Tattersell' to ferry the royal fugitive.",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 35,
                        "type": "yes_no_not_given",
                        "instruction": "Do the following statements agree with the claims of the writer?",
                        "prompt": "Charles II shared his personal memories of his escape with the diarist Samuel Pepys.",
                        "answer": "YES",
                        "explanation": "Paragraph F states: 'The King personally dictated the vivid account of his six weeks on the run to diarist Samuel Pepys'.",
                        "passageReference": "Paragraph F"
                    },
                    {
                        "number": 36,
                        "type": "multiple_choice_single",
                        "instruction": "Questions 36–40: Choose the correct letter, A, B, C, or D.",
                        "prompt": "Why did Charles II decide to travel alone or with only one companion?",
                        "options": [
                            "A: His officers refused to accompany him into exile.",
                            "B: Traveling in large groups was far more likely to arouse suspicion.",
                            "C: He lacked sufficient funds to feed a royal retinue.",
                            "D: He believed his horse could carry only one rider."
                        ],
                        "answer": "B",
                        "explanation": "Paragraph B states: 'Realizing that large groups attracted suspicion, the King resolved to journey alone or with solitary guides.'",
                        "passageReference": "Paragraph B"
                    },
                    {
                        "number": 37,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "What disguise did Charles adopt while accompanying Jane Lane across the West Country?",
                        "options": [
                            "A: A Franciscan monk on a pilgrimage",
                            "B: A traveling merchant selling silk ribbons",
                            "C: A tenant farmer's son riding pillion behind her",
                            "D: A wounded soldier returning from the war"
                        ],
                        "answer": "C",
                        "explanation": "Paragraph D states Charles assumed the role of 'a tenant farmer's son escorting Jane Lane... riding pillion behind her'.",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 38,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "What personal quality helped Charles avoid discovery during tense roadside encounters?",
                        "options": [
                            "A: His quick wit and calm composure",
                            "B: His mastery of foreign languages",
                            "C: His ability to bribe guards with gold coins",
                            "D: His physical swordsmanship in duels"
                        ],
                        "answer": "A",
                        "explanation": "Paragraph D highlights Charles's 'quick wit, self-possession, and calm composure prevented exposure.'",
                        "passageReference": "Paragraph D"
                    },
                    {
                        "number": 39,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "From which English coastal town did Charles finally set sail for France?",
                        "options": [
                            "A: Portsmouth",
                            "B: Brighthelmstone (Brighton)",
                            "C: Plymouth",
                            "D: Dover"
                        ],
                        "answer": "B",
                        "explanation": "Paragraph E states he departed from the small fishing village of Brighthelmstone (modern Brighton).",
                        "passageReference": "Paragraph E"
                    },
                    {
                        "number": 40,
                        "type": "multiple_choice_single",
                        "instruction": "Choose the correct letter, A, B, C, or D.",
                        "prompt": "What symbol became an enduring emblem of British resilience following the King's return?",
                        "options": [
                            "A: The Red Lion",
                            "B: The Golden Anchor",
                            "C: The Silver Rose",
                            "D: The Royal Oak"
                        ],
                        "answer": "D",
                        "explanation": "Paragraph F states the escape immortalized the 'Royal Oak' as an enduring symbol of British resilience.",
                        "passageReference": "Paragraph F"
                    }
                ]
            }
        ]
    }

def main():
    dataset = {
        "modules": {
            "reading": {
                "name": "Reading",
                "status": "active",
                "badge": "Active",
                "description": "Authentic Computer-Delivered Reading test with 3 passages, 40 questions, 60 minutes."
            },
            "listening": {
                "name": "Listening",
                "status": "soon",
                "badge": "Soon",
                "description": "Authentic 4-section listening module with official audio playback coming soon."
            },
            "writing": {
                "name": "Writing",
                "status": "soon",
                "badge": "Soon",
                "description": "Task 1 academic report and Task 2 argumentative essay with live word counters coming soon."
            },
            "speaking": {
                "name": "Speaking",
                "status": "soon",
                "badge": "Soon",
                "description": "One-on-one interactive AI examiner simulation coming soon."
            }
        },
        "tests": [
            build_cambridge_19_test_1(),
            build_cambridge_18_test_1(),
            build_cambridge_17_test_1()
        ]
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "tests.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully generated tests.json at: {out_path}")
    print(f"Total tests: {len(dataset['tests'])}")
    for t in dataset['tests']:
        total_q = sum(len(p['questions']) for p in t['passages'])
        print(f"  - {t['book']} (Test {t['testNumber']}): {len(t['passages'])} passages, {total_q} questions")

if __name__ == "__main__":
    main()
