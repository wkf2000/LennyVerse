# LennyVerse: AI-Powered Product Wisdom Platform
## Product Requirements Document (PRD)

# 1. Problem Statement

## The Gap
Lenny Rachitsky's archive — 638 documents, ~5.4M words spanning 7 years of product management wisdom — is one of the richest collections of practitioner knowledge ever assembled. Yet today, consuming it is linear and passive: you read posts, listen to episodes, or search Lennybot. There is no way to:

- **Navigate the knowledge spatially** — see how topics connect, where guests agree/disagree, how thinking evolved over time
- **Learn actively** — test your understanding, get personalized curricula, track mastery
- **Extract structured wisdom** — pull out frameworks, mental models, and decision templates from unstructured prose and conversation
- **Explore by need** — a teacher building a syllabus, a student learning PM fundamentals, and a practitioner solving a real problem each need different paths through the same archive

## The Opportunity
Transform passive consumption into an **interactive knowledge system** that makes Lenny's archive feel alive — navigable, teachable, and personally relevant — while showcasing Generative AI, Agentic AI, and Data Visualization as a cohesive product.

## Contest Fit
Lenny's 2026 contest (winner April 15th) rewards creative, novel uses of this data. The prior standout was LennyRPG — a gamified approach. LennyVerse must be equally inventive but occupy a different space: **the definitive way to explore, learn from, and apply product wisdom at scale.** It must clearly differentiate from Lennybot (Q&A chatbot) by being visual, agentic, and pedagogical.

# 2. Target Users

## Primary Personas

**1. Teacher / Coach (PM instructor, exec coach, bootcamp facilitator)**
- Wants: ready-made teaching materials, case studies, assessments, syllabi
- Behavior: builds curricula from the archive, exports materials, tracks cohort progress

**2. Student (MBA, bootcamp, self-taught)**
- Wants: structured learning, testable knowledge, progress tracking, portfolio-ready understanding
- Behavior: follows curricula sequentially, takes quizzes, revisits weak areas

**3. Product Manager (IC or lead)**
- Wants: actionable frameworks, decision support for real work situations, career growth guidance
- Behavior: searches for specific topics ("how to run a pricing experiment"), browses by theme, returns weekly

**4. General Practitioner (founder, growth lead, operator, aspiring PM)**
- Wants: curated wisdom on demand, quick answers to specific questions, inspiration from guest stories
- Behavior: browses casually via visualizations, searches for topics as needs arise, shares insights with their team

# 3. Product Vision

LennyVerse is a **knowledge universe** — an interactive, AI-powered platform where Lenny's 638 documents become an explorable galaxy of interconnected wisdom. Users don't just read — they navigate, discover, learn, and apply.

Three pillars, visible in the product:
- **Generative AI** — synthesizes, summarizes, generates quizzes, creates teaching materials, and answers questions grounded in the archive
- **Agentic AI** — autonomously builds personalized learning paths, adapts curricula based on progress, and proactively surfaces relevant content
- **Data Visualization** — makes the knowledge base tangible through interactive maps, timelines, relationship graphs, and progress dashboards

# 4. Consolidated Feature Set

All features listed with priority (P0 = must ship, P1 = should ship, P2 = nice to have, P3 = defer post-contest).

## Exploration & Visualization

| # | Feature | Description | Priority | AI Pillar |
|---|---------|-------------|----------|-----------|
| VIZ-1 | **Knowledge Galaxy** | The hero feature. Interactive visualization of the entire archive as an explorable galaxy/constellation map. Documents are stars; clusters are topics; brightness indicates influence/citation. Users zoom, filter by tag/guest/date, and click any star to read the content. Immediately communicates the scale and interconnectedness of 638 documents. | P0 | Data Viz |
| VIZ-2 | **Concept Map Navigator** | Interactive, zoomable visualization showing how concepts connect across the archive. Clicking a node (e.g., "retention") expands to show related concepts, key posts, key guests, and connections to adjacent topics like "engagement" and "activation." | P1 | Data Viz |
| VIZ-3 | **Timeline Explorer** | Interactive timeline (2019-2026) showing how topics, guest frequency, and themes evolved. Scrub through time to see what Lenny was writing about in any month. Filter by topic to see an idea's evolution. | P1 | Data Viz |
| VIZ-4 | **Guest Network Graph** | Interactive force-directed graph showing guest relationships: who appeared together, who referenced each other, who shares topics. Clicking a guest shows their profile and all connections. | P1 | Data Viz |

## Search & Discovery

| # | Feature | Description | Priority | AI Pillar |
|---|---------|-------------|----------|-----------|
| DSC-1 | **Semantic Search** | Full-text + semantic (vector) search across the entire archive. Results show excerpts with highlighted matches, relevance scores, and "find more like this." | P0 | Generative AI |
| DSC-2 | **Framework Library** | AI-extracted catalog of every PM framework, mental model, and heuristic across the archive (e.g., "ICE scoring," "Jobs to Be Done," "Racecar Growth Framework"). Each links to source documents, shows which guests advocate it, and includes a one-paragraph summary. | P0 | Generative AI |
| DSC-3 | **Guest Wisdom Profiles** | Rich profile pages for each of the 289 guests: key topics, signature frameworks, career timeline, all appearances, and AI-generated "What [Guest] would say about..." feature. | P1 | Generative AI |
| DSC-4 | **Decision Advisor** | User describes a real product decision ("Should I add a paywall?"). System retrieves relevant advice, synthesizes a structured recommendation: Pros, Cons, Frameworks to Apply, Case Studies, What Lenny's Guests Would Say — all with citations. | P1 | Generative AI |
| DSC-5 | **Topic Deep Dives** | For each of the 17 tags: an AI-curated landing page with the most important insights, a reading order, key disagreements between guests, and an evolution timeline (2019-2026). | P2 | Generative AI |
| DSC-6 | **Career Path Navigator** | Interactive visualization of PM career stages (IC → Senior → Lead → Director → VP → CPO) with relevant content mapped to each stage. User selects their level and goals; system highlights relevant content. | P2 | Data Viz |
| DSC-7 | **AI Chat (Contextual)** | Chat always grounded in the user's current context — the document they're reading, the learning path they're on, the topic they're exploring. "Ask about this" rather than "ask anything." | P2 | Generative AI |

## Learning & Assessment (Student)

| # | Feature | Description | Priority | AI Pillar |
|---|---------|-------------|----------|-----------|
| LRN-1 | **Agentic Learning Paths** | User states a learning goal ("I want to understand growth loops"). An AI agent autonomously builds a multi-week curriculum: ordered reading list, podcast episodes with specific timestamp ranges, embedded quizzes, and a capstone project. The path adapts as the student progresses — skipping mastered material, reinforcing weak areas. | P0 | Agentic AI |
| LRN-2 | **Interactive Quizzes** | AI-generated quizzes for any document or topic. Multiple formats: multiple choice, scenario-based ("You're a PM at a marketplace that's losing supply. What's your first move?"), and open-ended with AI grading. | P0 | Generative AI |
| LRN-3 | **Mastery Dashboard** | Visual progress tracker: topics explored, quizzes completed, mastery score per topic, streak tracking, and comparison to community averages. | P2 | Data Viz |
| LRN-4 | **Flashcard Generator** | AI generates spaced-repetition flashcards from any document or learning path. Integrates with the quiz system for progress tracking. | P2 | Generative AI |
| LRN-5 | **Study Mode** | Distraction-free reading experience with AI-powered sidebar: instant definitions, related content, "explain like I'm 5" for jargon, and inline quizzes. | P2 | Generative AI |

## Teaching & Curriculum (Teacher/Coach)

| # | Feature | Description | Priority | AI Pillar |
|---|---------|-------------|----------|-----------|
| TCH-1 | **Agentic Curriculum Builder** | Teacher specifies: course topic, duration, student level, learning objectives. An AI agent builds a complete syllabus: weekly modules, assigned readings (with highlighted sections), discussion questions, quizzes, and a final project. The agent iterates on the curriculum based on teacher feedback. | P1 | Agentic AI |
| TCH-2 | **Assessment Generator** | Teacher selects topics and difficulty. AI generates: quizzes, case study analyses, debate prompts, and rubrics — all grounded in specific archive content. Exportable as PDF or LMS-compatible format. | P3 | Generative AI |
| TCH-3 | **Case Study Packager** | AI extracts and packages podcast stories into structured teaching case studies: Background, Challenge, Decision Point, Outcome, Discussion Questions. Classroom-ready. | P3 | Generative AI |
| TCH-4 | **Cohort Dashboard** | Teacher creates a cohort, assigns a learning path, and tracks aggregate progress: completion rates, quiz scores, areas of struggle. | P3 | Data Viz |
| TCH-5 | **Lesson Plan Export** | Any combination of content, quizzes, and discussion questions exportable as a formatted lesson plan (PDF, Google Slides, Notion). | P3 | — |

## Engagement & Retention

| # | Feature | Description | Priority | AI Pillar |
|---|---------|-------------|----------|-----------|
| ENG-1 | **"Wisdom of the Day"** | Daily AI-generated insight from the archive — a surprising connection, a contrarian viewpoint, or a timeless principle. Shareable as a social card. | P2 | Generative AI |
| ENG-2 | **Bookmarks & Collections** | Users bookmark content and organize into personal collections (e.g., "My Growth Reading List"). Collections can be shared publicly. | P2 | — |
| ENG-3 | **"Lenny's Take" Digest** | AI-generated periodic digest surfacing the most relevant archive content based on the user's recent activity, role, and stated interests. | P3 | Generative AI |

# 5. Priority Summary

## P0 — Must Ship (Core Experience)
These features define the product. Without them, LennyVerse doesn't exist.

- **VIZ-1 Knowledge Galaxy** — hero visual, the "whoa" moment (Data Viz)
- **DSC-1 Semantic Search** — utility backbone (Generative AI)
- **DSC-2 Framework Library** — structured value for PMs (Generative AI)
- **LRN-1 Agentic Learning Paths** — adaptive curricula, the pedagogical core (Agentic AI)
- **LRN-2 Interactive Quizzes** — active learning + assessment (Generative AI)

**Rationale:** These five features hit all three AI pillars, serve all four personas, and create a product that is visually stunning (Galaxy), deeply useful (Search, Frameworks), pedagogically novel (Learning Paths, Quizzes), and clearly differentiated from Lennybot.

## P1 — Should Ship (Differentiation)
Elevate LennyVerse from "good" to "contest winner."

- **VIZ-2 Concept Map Navigator** — second major visualization (Data Viz)
- **VIZ-3 Timeline Explorer** — temporal dimension (Data Viz)
- **VIZ-4 Guest Network Graph** — relationship dimension (Data Viz)
- **DSC-3 Guest Wisdom Profiles** — makes 289 guests browsable (Generative AI)
- **DSC-4 Decision Advisor** — structured decision support (Generative AI)
- **TCH-1 Agentic Curriculum Builder** — the teacher's killer feature (Agentic AI)

## P2 — Nice to Have (Polish & Depth)
- DSC-5 Topic Deep Dives
- DSC-6 Career Path Navigator
- DSC-7 AI Chat (Contextual)
- LRN-3 Mastery Dashboard
- LRN-4 Flashcard Generator
- LRN-5 Study Mode
- ENG-1 Wisdom of the Day
- ENG-2 Bookmarks & Collections

## P3 — Defer (Post-Contest)
- TCH-2 Assessment Generator — requires TCH-1 first
- TCH-3 Case Study Packager — valuable but not contest-critical
- TCH-4 Cohort Dashboard — requires multi-user infra
- TCH-5 Lesson Plan Export — depends on TCH-1 + TCH-2
- ENG-3 "Lenny's Take" Digest — requires email infra

# 6. User Journeys

## Journey 1: First-Time Visitor (any persona)
1. **Lands on LennyVerse** → sees the Knowledge Galaxy visualization, immediately understands the scale (638 documents, 289 guests, 5.4M words)
2. **Explores the Galaxy** → zooms into a cluster (e.g., "Growth"), sees stars (documents) light up, clicks one
3. **Reads a document** → sees AI-generated summary, key frameworks extracted, related content suggested
4. **Prompted to learn** → "Want to master Growth? Start a learning path" → enters the agentic learning flow
5. **Takes a quiz** → tests understanding of what they just read, gets instant feedback with citations
6. **Hooked** → bookmarks content, starts a learning path, returns tomorrow

## Journey 2: PM Solving a Real Problem
1. **Searches** → "How do I set pricing for a new feature?"
2. **Gets structured results** → Relevant posts + episodes, ranked by relevance, with highlighted excerpts
3. **Opens Framework Library** → finds "Pricing Frameworks" with 4 frameworks from different guests
4. **Uses Decision Advisor** → describes their specific situation, gets synthesized advice citing 6 different sources
5. **Explores the Guest Profiles** → clicks through to the guests who've discussed pricing, reads their full profiles

## Journey 3: Student Following a Learning Path
1. **States a goal** → "I want to learn product strategy from scratch"
2. **Agent builds a path** → 6-week curriculum with weekly modules, each containing: readings, podcast clips, quizzes, and a mini-project
3. **Progresses through Week 1** → reads assigned posts, listens to highlighted podcast segments, takes end-of-module quiz
4. **Agent adapts** → student aced "competitive analysis" but struggled on "moats" → agent adds supplementary content on moats, skips review content on competitive analysis
5. **Completes the path** → gets a mastery summary showing strengths and areas for continued growth

## Journey 4: Teacher Building a Course
1. **Opens Curriculum Builder** → specifies "8-week Product Management Fundamentals course for MBA students"
2. **Agent generates syllabus** → weekly topics, assigned readings from the archive, discussion questions, quiz questions
3. **Teacher iterates** → "Add more content on metrics" → agent adjusts Week 4, adds a metrics-focused case study
4. **Teacher exports** → downloads lesson plans, quiz banks, and reading lists

# 7. Key Differentiators vs. Existing Products

| vs. | LennyVerse Advantage |
|-----|---------------------|
| **Lennybot** | Lennybot is a chatbot. LennyVerse is a visual, navigable, pedagogical knowledge system. You don't just ask questions — you explore, learn, and build mastery. |
| **LennyRPG** | LennyRPG gamifies trivia. LennyVerse creates genuine learning outcomes with adaptive curricula, structured frameworks, and progress tracking. |
| **Reading the archive** | Linear, passive, overwhelming. LennyVerse makes it spatial, active, and personalized. |
| **Generic AI chatbots** | Not grounded in the archive. LennyVerse's every answer is cited and traceable to specific Lenny content. |

# 8. Success Metrics (Contest Judging Criteria)

- **First impression** — Does the Knowledge Galaxy make someone say "whoa" in the first 5 seconds?
- **AI integration depth** — Are all three pillars (Generative, Agentic, Visualization) clearly visible and tightly integrated?
- **Utility** — Can a PM actually use this to make better decisions tomorrow?
- **Novelty** — Has anything like this been done with a content archive before?
- **Polish** — Does it feel like a product, not a prototype?
- **Pedagogical value** — Would a PM instructor actually assign this to students?

# 9. Open Questions

1. **Authentication** — Should we require login for personalized features (learning paths, progress), or keep the entire experience anonymous for frictionless contest judging?
2. **Content scope** — Should we process all 638 documents for launch, or start with a curated subset and expand?
3. **LLM cost management** — Agentic features (curriculum builder, decision advisor) have non-trivial API costs. Should we pre-generate common curricula and cache aggressively?
4. **Mobile experience** — Is the Knowledge Galaxy visualization mobile-friendly, or should we design a different mobile entry point?
5. **Lenny's brand** — How closely should the visual identity mirror Lenny's existing brand (newsletter, podcast)?
