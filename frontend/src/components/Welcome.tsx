import {
  AlertTriangle,
  ArrowRight,
  Bot,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  CloudSun,
  Compass,
  FileDown,
  Hotel,
  MapPin,
  Plane,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Star,
  Users,
  Wallet,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import type { Health } from '../lib/api';
import Composer from './Composer';

interface Props {
  onSubmit: (text: string) => void;
  health: Health | null;
  healthError: boolean;
  onGetStarted?: () => void;
}

const VIBE_OPTIONS = [
  '🏛️ Culture & Museums',
  '🍷 Food & Wine',
  '🏖️ Beaches & Sun',
  '🌲 Nature & Hiking',
  '⚡ Adventure & Sports',
  '🛍️ Shopping & Nightlife',
  '🧘 Relaxation & Wellness',
  '💎 Luxury & Fine Dining',
];

const CURATED_ESCAPES = [
  {
    title: 'Lisbon & Sintra',
    country: 'Portugal',
    duration: '4 Days',
    budget: '€900 total',
    travelers: '2 Travelers',
    tag: 'Trending',
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    prompt: 'Long weekend in Lisbon from Madrid for 2, around €900. Focus on historic neighborhoods, authentic seafood, and a day trip to Sintra.',
    highlights: ['Pastéis de Belém', 'Tram 28 Tour', 'Pena Palace Sintra', 'Miradouro Sunsets'],
  },
  {
    title: 'Tokyo & Kyoto',
    country: 'Japan',
    duration: '7 Days',
    budget: '$3,500 total',
    travelers: '2 Travelers',
    tag: 'Bucket List',
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    prompt: 'A 7-day trip to Tokyo and Kyoto from New York for 2 people with a $3,500 budget in April. We love sushi, ancient temples, Shibuya, and anime culture.',
    highlights: ['Tsukiji Fish Market', 'Shibuya Crossing', 'Fushimi Inari', 'Akihabara Tech'],
  },
  {
    title: 'Rome Highlights',
    country: 'Italy',
    duration: '5 Days',
    budget: '€1,800 total',
    travelers: '2 Travelers',
    tag: 'Romantic',
    gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    prompt: 'Romantic 5-day trip to Rome from London for 2 people with €1,800 budget. 4-star boutique hotel near Pantheon, private Colosseum visit, and Trastevere food walk.',
    highlights: ['Colosseum & Forum', 'Trevi Fountain', 'Vatican Museums', 'Trastevere Dining'],
  },
  {
    title: 'Amsterdam Canals',
    country: 'Netherlands',
    duration: '5 Days',
    budget: '€2,200 total',
    travelers: '2 Travelers',
    tag: 'Culture',
    gradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    prompt: 'Plan a 5-day food and museum trip from Madrid to Amsterdam for 2 people with a €2,200 budget next month.',
    highlights: ['Rijksmuseum', 'Evening Canal Cruise', 'Jordaan Cafes', 'Vondelpark Strolls'],
  },
  {
    title: 'Goa Coastal Retreat',
    country: 'India',
    duration: '6 Days',
    budget: '₹60,000 total',
    travelers: '4 Friends',
    tag: 'Budget Best',
    gradient: 'linear-gradient(135deg, #ff0844 0%, #ffb199 100%)',
    prompt: 'Cheap beach week in Goa from Delhi, 4 friends, ₹60,000 total budget. Great seafood shacks, sunset cruises, and scooter exploration in South Goa.',
    highlights: ['Palolem Beach', 'Old Goa Cathedrals', 'Sunset Cruise', 'Beachside Shacks'],
  },
];

const SHOWCASE_TABS = [
  {
    id: 'itinerary',
    title: 'Day-by-Day Schedule & Map',
    subtitle: 'Interactive Leaflet/MapLibre route mapping with weather-adaptive scheduling.',
    image: '/screenshots/screenshot03.png',
  },
  {
    id: 'flights',
    title: 'Live Flight Comparison',
    subtitle: 'Real-time airfares scoring duration vs stops with instant alternative re-pricing.',
    image: '/screenshots/screenshot05.png',
  },
  {
    id: 'hotels',
    title: 'Vetted Stays & Accommodations',
    subtitle: 'Location-grounded hotels scored by guest ratings and budget fit.',
    image: '/screenshots/screenshot06.png',
  },
  {
    id: 'budget',
    title: 'Visual Budget Breakdown',
    subtitle: 'Deterministic cost calculation tracking flight, stay, and daily allowances.',
    image: '/screenshots/screenshot04.png',
  },
  {
    id: 'timeline',
    title: 'Multi-Agent Activity Stream',
    subtitle: 'Live Server-Sent Events tracing concurrent execution across all specialized agents.',
    image: '/screenshots/screenshot07.png',
  },
];

const FAQS = [
  {
    q: 'How does Wayfinder differ from standard chatbots like ChatGPT or Claude?',
    a: 'Traditional LLM chatbots generate generic text with made-up flight numbers, guessed prices, and hallucinated hotel coordinates. Wayfinder uses a stateful LangGraph multi-agent architecture: 4 micro-agents query live APIs (flights, hotels, weather, and OpenStreetMap) concurrently, and an exact mathematical solver manages your budget without arithmetic guesswork.',
  },
  {
    q: 'Can I swap flights or hotels after the plan is generated?',
    a: 'Yes! Wayfinder supports Human-in-the-Loop interaction. When viewing the generated dossier, simply click any alternative flight or hotel card. The agent immediately re-prices the entire trip and adapts the day-by-day plan around your updated schedule and base.',
  },
  {
    q: 'How does the weather-adaptive scheduler work?',
    a: 'The Weather agent pulls high-resolution 14-day forecasts from Open-Meteo. When synthesizing the daily plan, the agent automatically assigns outdoor walking tours, beach visits, and viewpoints to sunny windows, while reserving museums, galleries, and covered markets for overcast or rainy days.',
  },
  {
    q: 'How do I export my trip to my phone or calendar?',
    a: 'Once approved, you can export a standardized RFC 5545 .ics calendar file that imports into Google Calendar, Apple Calendar, and Outlook with one tap. You can also send the formatted HTML & plaintext itinerary directly to your email inbox, or print a dossier to PDF.',
  },
  {
    q: 'What LLMs power Wayfinder?',
    a: 'Wayfinder utilizes an intelligent multi-provider fallback chain starting with ultra-fast Groq (Qwen 3.8 27B), cascading to Google Gemini (gemini-3.8-flash), and Hugging Face Inference for high reliability and zero downtime.',
  },
];

export default function Welcome({ onSubmit, health, healthError, onGetStarted }: Props) {
  const [plannerTab, setPlannerTab] = useState<'builder' | 'prompt'>('builder');
  const [activeShowcase, setActiveShowcase] = useState(0);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  // Quick Builder Form State
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [dates, setDates] = useState('');
  const [budget, setBudget] = useState('');
  const [travelers, setTravelers] = useState('2 people');
  const [selectedVibes, setSelectedVibes] = useState<string[]>(['🏛️ Culture & Museums', '🍷 Food & Wine']);
  const [extraNotes, setExtraNotes] = useState('');
  const [formError, setFormError] = useState('');

  const toggleVibe = (vibe: string) => {
    setSelectedVibes((prev) => (prev.includes(vibe) ? prev.filter((v) => v !== vibe) : [...prev, vibe]));
  };

  const handleQuickBuilderSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination.trim()) {
      setFormError('Please enter a destination to get started.');
      return;
    }
    setFormError('');

    let prompt = `Plan a trip to ${destination.trim()}`;
    if (origin.trim()) prompt += ` from ${origin.trim()}`;
    if (dates.trim()) prompt += ` for ${dates.trim()}`;
    if (travelers.trim()) prompt += ` for ${travelers.trim()}`;
    if (budget.trim()) prompt += ` with a budget of ${budget.trim()}`;
    if (selectedVibes.length > 0) {
      const cleanVibes = selectedVibes.map((v) => v.replace(/^[\p{Emoji}\s]+/u, '').trim());
      prompt += `. Focused on: ${cleanVibes.join(', ')}`;
    }
    if (extraNotes.trim()) prompt += `. Preferences: ${extraNotes.trim()}`;

    onSubmit(prompt);
  };

  const noModel = health && health.llm_providers.length === 0;

  return (
    <div className="landing">
      {/* ---------- HERO SECTION & PLANNER ---------- */}
      <section className="landing-hero" id="planner">
        <div className="landing-hero__ambient" aria-hidden="true" />
        <div className="landing-container">
          <div className="landing-hero__badge">
            <span className="landing-hero__badge-pulse" />
            <Sparkles size={14} className="landing-hero__badge-icon" />
            <span>Autonomous Multi-Agent Travel Planner</span>
          </div>

          <h1 className="landing-hero__title">
            Tailor-made journeys, crafted by <span className="text-gradient">Autonomous AI</span>
          </h1>

          <p className="landing-hero__lead">
            Tell Wayfinder where and when you want to travel. Four specialized AI agents coordinate in parallel to find
            live flights, compare vetted stays, check real-time forecasts, and optimize your budget into an immaculate,
            day-by-day itinerary.
          </p>

          {/* TELEMETRY STATUS PILLS */}
          <div className="landing-telemetry">
            <div className="telemetry-pill">
              <span className="telemetry-pill__dot telemetry-pill__dot--green" />
              <span>
                {health?.llm_providers?.length
                  ? `AI Providers: ${health.llm_providers.join(', ')} active`
                  : 'Multi-LLM Engine Ready'}
              </span>
            </div>
            <div className="telemetry-pill">
              <Plane size={13} className="telemetry-pill__icon" />
              <span>{health?.live_travel_data ? 'SerpAPI Live Flight & Hotel Data' : 'Live Open-Meteo & OpenStreetMap'}</span>
            </div>
            <div className="telemetry-pill">
              <ShieldCheck size={13} className="telemetry-pill__icon" />
              <span>Zero-Hallucination Budget Solver</span>
            </div>
          </div>

          {/* SYSTEM CALLOUTS */}
          {healthError && (
            <div className="callout callout--error landing-callout" role="alert">
              <AlertTriangle size={18} aria-hidden />
              <div>
                <strong>Can&apos;t reach the backend server.</strong> Please verify the backend is running on{' '}
                <code>http://localhost:8000</code>.
              </div>
            </div>
          )}
          {noModel && (
            <div className="callout callout--error landing-callout" role="alert">
              <AlertTriangle size={18} aria-hidden />
              <div>
                <strong>No AI model key detected.</strong> Configure <code>GROQ_API_KEY</code> or <code>GOOGLE_API_KEY</code> in{' '}
                <code>backend/.env</code>.
              </div>
            </div>
          )}

          {/* INTERACTIVE PLANNER / GET STARTED WIDGET */}
          <div className="planner-card" id="planner-widget">
            <div className="planner-card__header">
              <div className="planner-card__tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={plannerTab === 'builder'}
                  className={`planner-card__tab ${plannerTab === 'builder' ? 'is-active' : ''}`}
                  onClick={() => setPlannerTab('builder')}
                >
                  <Sparkles size={16} />
                  <span>Quick Trip Builder</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={plannerTab === 'prompt'}
                  className={`planner-card__tab ${plannerTab === 'prompt' ? 'is-active' : ''}`}
                  onClick={() => setPlannerTab('prompt')}
                >
                  <Send size={15} />
                  <span>Natural Language Prompt</span>
                </button>
              </div>
              <span className="planner-card__hint">
                {plannerTab === 'builder' ? 'Structured instant planner' : 'Chat directly with full context'}
              </span>
            </div>

            {plannerTab === 'builder' ? (
              <form onSubmit={handleQuickBuilderSubmit} className="planner-form">
                <div className="planner-form__grid">
                  {/* FROM */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <Plane size={15} /> Leaving From
                    </label>
                    <input
                      type="text"
                      className="planner-form__input"
                      placeholder="e.g. London, New York, Mumbai"
                      value={origin}
                      onChange={(e) => setOrigin(e.target.value)}
                    />
                  </div>

                  {/* TO */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <MapPin size={15} /> Destination <span className="planner-form__req">*</span>
                    </label>
                    <input
                      type="text"
                      className="planner-form__input"
                      placeholder="e.g. Amsterdam, Tokyo, Rome"
                      value={destination}
                      required
                      onChange={(e) => {
                        setDestination(e.target.value);
                        if (formError) setFormError('');
                      }}
                    />
                  </div>

                  {/* DATES / DURATION */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <Calendar size={15} /> Dates or Duration
                    </label>
                    <input
                      type="text"
                      className="planner-form__input"
                      placeholder="e.g. 5 days in April, Dec 10–16"
                      value={dates}
                      onChange={(e) => setDates(e.target.value)}
                    />
                  </div>

                  {/* BUDGET */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <Wallet size={15} /> Total Budget
                    </label>
                    <input
                      type="text"
                      className="planner-form__input"
                      placeholder="e.g. €2,500, $3,000, ₹80,000"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                    />
                  </div>

                  {/* TRAVELERS */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <Users size={15} /> Travelers
                    </label>
                    <select
                      className="planner-form__select"
                      value={travelers}
                      onChange={(e) => setTravelers(e.target.value)}
                    >
                      <option value="1 solo traveler">1 Solo Traveler</option>
                      <option value="2 people">2 Travelers (Couple / Friends)</option>
                      <option value="3 travelers">3 Travelers</option>
                      <option value="4 people (family/group)">4 Travelers (Family / Group)</option>
                      <option value="5+ travelers group">5+ Group</option>
                    </select>
                  </div>

                  {/* PREFERENCES / NOTES */}
                  <div className="planner-form__field">
                    <label className="planner-form__label">
                      <Compass size={15} /> Stays & Preferences
                    </label>
                    <input
                      type="text"
                      className="planner-form__input"
                      placeholder="e.g. 4-star boutique hotel, direct flights"
                      value={extraNotes}
                      onChange={(e) => setExtraNotes(e.target.value)}
                    />
                  </div>
                </div>

                {/* STYLE VIBES */}
                <div className="planner-form__vibes">
                  <span className="planner-form__vibes-title">Select travel interests:</span>
                  <div className="planner-form__vibes-list">
                    {VIBE_OPTIONS.map((vibe) => {
                      const active = selectedVibes.includes(vibe);
                      return (
                        <button
                          key={vibe}
                          type="button"
                          className={`vibe-chip ${active ? 'is-selected' : ''}`}
                          onClick={() => toggleVibe(vibe)}
                        >
                          {vibe}
                          {active && <Check size={14} className="vibe-chip__check" />}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {formError && <div className="planner-form__error">{formError}</div>}

                {/* SUBMIT BUTTON */}
                <div className="planner-form__actions">
                  <button type="submit" className="btn-get-started">
                    <Sparkles size={18} />
                    <span>Plan My Journey with AI</span>
                    <ArrowRight size={18} />
                  </button>
                </div>
              </form>
            ) : (
              <div className="planner-prompt-view">
                <Composer
                  variant="hero"
                  autoFocus
                  onSubmit={onSubmit}
                  placeholder="e.g. Plan a 5-day food and museum trip from Madrid to Amsterdam for 2 people with a €2,500 budget next month."
                />
                <p className="planner-prompt-view__tip">
                  💡 Tip: Include your departure city, target destination, number of travelers, and estimated budget for the most accurate optimization.
                </p>
              </div>
            )}
          </div>

          {/* CURATED IDEAS / QUICK CHIPS */}
          <div className="hero-quick-escapes">
            <span className="hero-quick-escapes__label">Or pick a popular curated trip:</span>
            <div className="hero-quick-escapes__grid">
              {CURATED_ESCAPES.slice(0, 4).map((escape) => (
                <button
                  key={escape.title}
                  type="button"
                  className="quick-escape-pill"
                  onClick={() => onSubmit(escape.prompt)}
                >
                  <span className="quick-escape-pill__badge">{escape.duration}</span>
                  <span className="quick-escape-pill__title">{escape.title}</span>
                  <span className="quick-escape-pill__budget">{escape.budget}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---------- VALUE STATS BAR ---------- */}
      <section className="stats-bar">
        <div className="landing-container">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-card__number">4 Micro-Agents</div>
              <div className="stat-card__label">Flights, Stays, Places & Weather fan-out in parallel</div>
            </div>
            <div className="stat-card">
              <div className="stat-card__number">&lt; 30 Seconds</div>
              <div className="stat-card__label">Full end-to-end trip design, pricing & mapping</div>
            </div>
            <div className="stat-card">
              <div className="stat-card__number">100% Deterministic</div>
              <div className="stat-card__label">Exact mathematical scoring with zero arithmetic hallucinations</div>
            </div>
            <div className="stat-card">
              <div className="stat-card__number">3 Universal Exports</div>
              <div className="stat-card__label">Apple/Google Calendar (.ics), rich HTML email & PDF dossier</div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- HOW IT WORKS ---------- */}
      <section className="section" id="how-it-works">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Autonomous Execution</div>
            <h2 className="section-title">From Prompt to Itinerary in 4 Autonomous Steps</h2>
            <p className="section-lead">
              Unlike chatbots that merely regurgitate text, Wayfinder executes a stateful Directed Acyclic Graph (DAG) with
              strict data validation and persistence.
            </p>
          </div>

          <div className="steps-grid">
            <div className="step-card">
              <div className="step-card__num">01</div>
              <div className="step-card__icon-box">
                <Bot size={24} />
              </div>
              <h3 className="step-card__title">Structured Intent Parsing</h3>
              <p className="step-card__desc">
                The parser extracts departure points, dates, headcounts, budget ceilings, and vibes into a validated Pydantic v2 schema.
              </p>
            </div>

            <div className="step-card">
              <div className="step-card__num">02</div>
              <div className="step-card__icon-box">
                <Zap size={24} />
              </div>
              <h3 className="step-card__title">Parallel Agent Fan-Out</h3>
              <p className="step-card__desc">
                Four independent agents scour live flight data, curated accommodations, OpenStreetMap points of interest, and 14-day Open-Meteo forecasts simultaneously.
              </p>
            </div>

            <div className="step-card">
              <div className="step-card__num">03</div>
              <div className="step-card__icon-box">
                <ShieldCheck size={24} />
              </div>
              <h3 className="step-card__title">Deterministic Budget Solver</h3>
              <p className="step-card__desc">
                Unit-tested mathematical algorithms balance flight layovers vs costs, match top-rated stays, and allocate daily spend limits without hallucinating.
              </p>
            </div>

            <div className="step-card">
              <div className="step-card__num">04</div>
              <div className="step-card__icon-box">
                <RefreshCw size={24} />
              </div>
              <h3 className="step-card__title">Interactive Customization</h3>
              <p className="step-card__desc">
                Review your interactive vector map, switch flights or hotels with instant dynamic re-pricing, and export directly to your calendar or email.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- CORE FEATURES GRID ---------- */}
      <section className="section section--surface" id="features">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Platform Capabilities</div>
            <h2 className="section-title">Engineered for Confident, Stress-Free Travel</h2>
            <p className="section-lead">
              Every detail is grounded in verified real-world data, from airport codes to opening hours and rain probabilities.
            </p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--red">
                <Plane size={22} />
              </div>
              <h3 className="feature-card__title">Live Flight Comparison</h3>
              <p className="feature-card__desc">
                Real-time airline routes comparing nonstop convenience with budget savings. Travelers can select any flight alternative and watch the plan automatically re-price.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--green">
                <Hotel size={22} />
              </div>
              <h3 className="feature-card__title">Curated Stays & Proximity</h3>
              <p className="feature-card__desc">
                Accommodations scored by guest reviews, walking proximity to key attractions, and target nightly budget. Swap between hotels with a single click.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--blue">
                <CloudSun size={22} />
              </div>
              <h3 className="feature-card__title">Weather-Adaptive Scheduling</h3>
              <p className="feature-card__desc">
                Live 14-day forecasts automatically arrange walking tours, viewpoints, and outdoor meals on clear sunny days, while slotting museums and indoor dining on rainy days.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--amber">
                <MapPin size={22} />
              </div>
              <h3 className="feature-card__title">Vector Route Mapping</h3>
              <p className="feature-card__desc">
                Every stop is geo-grounded via OpenStreetMap Nominatim and rendered on high-performance vector tiles. Visual day routes eliminate confusing zig-zag travel.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--purple">
                <RefreshCw size={22} />
              </div>
              <h3 className="feature-card__title">Human-in-the-Loop Re-Planning</h3>
              <p className="feature-card__desc">
                The agent pauses at critical milestones. Chat feedback like &ldquo;add more local foodie markets&rdquo; or select a new hotel to trigger dynamic re-planning on the fly.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-card__icon feature-card__icon--cyan">
                <FileDown size={22} />
              </div>
              <h3 className="feature-card__title">Universal Calendar & Email Sync</h3>
              <p className="feature-card__desc">
                Export standard RFC 5545 .ics calendars for Apple, Google, and Outlook, receive styled HTML itineraries in your inbox, or print a formatted PDF dossier.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- PRODUCT SHOWCASE GALLERY ---------- */}
      <section className="section" id="showcase">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Live Dossier Interface</div>
            <h2 className="section-title">A Full Interactive Travel Dossier</h2>
            <p className="section-lead">
              Wayfinder gives you an interactive travel canvas complete with schedule cards, vector maps, and cost progress bars.
            </p>
          </div>

          <div className="showcase-box">
            <div className="showcase-nav">
              {SHOWCASE_TABS.map((tab, idx) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`showcase-nav__item ${activeShowcase === idx ? 'is-active' : ''}`}
                  onClick={() => setActiveShowcase(idx)}
                >
                  <span className="showcase-nav__num">0{idx + 1}</span>
                  <span className="showcase-nav__title">{tab.title}</span>
                </button>
              ))}
            </div>

            <div className="showcase-preview">
              <div className="showcase-preview__chrome">
                <span className="showcase-preview__dot showcase-preview__dot--red" />
                <span className="showcase-preview__dot showcase-preview__dot--yellow" />
                <span className="showcase-preview__dot showcase-preview__dot--green" />
                <span className="showcase-preview__url">wayfinder.app/trips/amsterdam-dossier</span>
              </div>
              <div className="showcase-preview__content">
                <img
                  src={SHOWCASE_TABS[activeShowcase].image}
                  alt={SHOWCASE_TABS[activeShowcase].title}
                  className="showcase-preview__img"
                />
              </div>
              <div className="showcase-preview__caption">
                <strong>{SHOWCASE_TABS[activeShowcase].title}</strong>: {SHOWCASE_TABS[activeShowcase].subtitle}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- CURATED ESCAPES GALLERY ---------- */}
      <section className="section section--surface" id="inspirations">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Trip Inspirations</div>
            <h2 className="section-title">Trending Escapes Ready to Plan</h2>
            <p className="section-lead">
              Need inspiration? Pick any curated destination to immediately generate a fully-customized, live-priced itinerary.
            </p>
          </div>

          <div className="curated-grid">
            {CURATED_ESCAPES.map((escape) => (
              <div key={escape.title} className="escape-card">
                <div className="escape-card__header" style={{ background: escape.gradient }}>
                  <span className="escape-card__tag">{escape.tag}</span>
                  <div className="escape-card__header-info">
                    <span className="escape-card__country">{escape.country}</span>
                    <h3 className="escape-card__title">{escape.title}</h3>
                  </div>
                </div>

                <div className="escape-card__body">
                  <div className="escape-card__specs">
                    <span className="escape-card__spec">
                      <Calendar size={14} /> {escape.duration}
                    </span>
                    <span className="escape-card__spec">
                      <Users size={14} /> {escape.travelers}
                    </span>
                    <span className="escape-card__spec escape-card__spec--budget">
                      <Wallet size={14} /> {escape.budget}
                    </span>
                  </div>

                  <div className="escape-card__highlights">
                    <span className="escape-card__hl-title">Highlights:</span>
                    <div className="escape-card__hl-list">
                      {escape.highlights.map((h) => (
                        <span key={h} className="escape-card__hl-pill">
                          <CheckCircle2 size={12} /> {h}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="escape-card__cta"
                    onClick={() => onSubmit(escape.prompt)}
                  >
                    <span>Plan This Trip</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- TRAVELER TESTIMONIALS ---------- */}
      <section className="section">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Traveler Stories</div>
            <h2 className="section-title">Loved by Travelers Worldwide</h2>
            <p className="section-lead">See what real explorers say about switching from tabs to Wayfinder AI.</p>
          </div>

          <div className="testimonials-grid">
            <div className="testi-card">
              <div className="testi-card__stars">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={16} className="star-filled" />
                ))}
              </div>
              <p className="testi-card__quote">
                &ldquo;Wayfinder organized our 5-day Amsterdam trip in under a minute. The flight alternatives and weather-adapted museum days were completely spot-on!&rdquo;
              </p>
              <div className="testi-card__author">
                <div className="testi-card__avatar">ER</div>
                <div>
                  <div className="testi-card__name">Elena R.</div>
                  <div className="testi-card__role">Madrid &rarr; Amsterdam</div>
                </div>
              </div>
            </div>

            <div className="testi-card">
              <div className="testi-card__stars">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={16} className="star-filled" />
                ))}
              </div>
              <p className="testi-card__quote">
                &ldquo;The budget math is what sold me. Most AI tools hallucinate prices, but Wayfinder&apos;s deterministic solver stayed right within our €2,000 budget.&rdquo;
              </p>
              <div className="testi-card__author">
                <div className="testi-card__avatar">MK</div>
                <div>
                  <div className="testi-card__name">Marcus K.</div>
                  <div className="testi-card__role">Berlin &rarr; Lisbon</div>
                </div>
              </div>
            </div>

            <div className="testi-card">
              <div className="testi-card__stars">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} size={16} className="star-filled" />
                ))}
              </div>
              <p className="testi-card__quote">
                &ldquo;Exporting directly into Apple Calendar with exact times and locations was incredible. Saved us at least 6 hours of manual planning.&rdquo;
              </p>
              <div className="testi-card__author">
                <div className="testi-card__avatar">PS</div>
                <div>
                  <div className="testi-card__name">Priya S.</div>
                  <div className="testi-card__role">Bengaluru &rarr; Tokyo</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- FAQ SECTION ---------- */}
      <section className="section section--surface" id="faq">
        <div className="landing-container">
          <div className="section-header">
            <div className="section-badge">Got Questions?</div>
            <h2 className="section-title">Frequently Asked Questions</h2>
            <p className="section-lead">Everything you need to know about Wayfinder&apos;s multi-agent travel engine.</p>
          </div>

          <div className="faq-list">
            {FAQS.map((faq, i) => {
              const isOpen = openFaq === i;
              return (
                <div key={i} className={`faq-item ${isOpen ? 'is-open' : ''}`}>
                  <button
                    type="button"
                    className="faq-item__trigger"
                    onClick={() => setOpenFaq(isOpen ? null : i)}
                    aria-expanded={isOpen}
                  >
                    <span className="faq-item__question">{faq.q}</span>
                    <ChevronDown size={18} className={`faq-item__chevron ${isOpen ? 'is-rotated' : ''}`} />
                  </button>
                  {isOpen && <div className="faq-item__answer">{faq.a}</div>}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ---------- BOTTOM CTA BANNER ---------- */}
      <section className="cta-banner">
        <div className="landing-container">
          <div className="cta-banner__card">
            <div className="cta-banner__glow" aria-hidden="true" />
            <div className="cta-banner__badge">
              <Sparkles size={14} /> Ready to Take Off?
            </div>
            <h2 className="cta-banner__title">Start Planning Your Next Journey Today</h2>
            <p className="cta-banner__desc">
              Say goodbye to 20 open browser tabs. Let our autonomous AI agents design your complete, budget-optimized travel dossier in seconds.
            </p>
            <div className="cta-banner__actions">
              <button
                type="button"
                className="btn-get-started btn-get-started--large"
                onClick={onGetStarted}
              >
                <Sparkles size={18} />
                <span>Get Started — It&apos;s Free</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ---------- FOOTER ---------- */}
      <footer className="landing-footer">
        <div className="landing-container">
          <div className="landing-footer__top">
            <div className="landing-footer__brand">
              <div className="landing-footer__logo-row">
                <img src="/logo-mark.png" alt="" width="28" height="28" />
                <span className="landing-footer__name">Wayfinder</span>
              </div>
              <p className="landing-footer__tagline">
                Autonomous multi-agent travel intelligence powered by LangGraph, FastAPI, and React.
              </p>
            </div>

            <div className="landing-footer__links">
              <div className="landing-footer__col">
                <span className="landing-footer__heading">Navigation</span>
                <button type="button" className="footer-link" onClick={onGetStarted}>Plan Trip</button>
                <a href="#how-it-works" className="footer-link">How It Works</a>
                <a href="#features" className="footer-link">Features</a>
                <a href="#showcase" className="footer-link">Showcase</a>
                <a href="#inspirations" className="footer-link">Inspirations</a>
                <a href="#faq" className="footer-link">FAQ</a>
              </div>

              <div className="landing-footer__col">
                <span className="landing-footer__heading">Built With</span>
                <span className="footer-badge">LangGraph 0.6+</span>
                <span className="footer-badge">FastAPI 0.115+</span>
                <span className="footer-badge">React 18 & Vite</span>
                <span className="footer-badge">MapLibre GL</span>
                <span className="footer-badge">Groq & Gemini</span>
              </div>
            </div>
          </div>

          <div className="landing-footer__bottom">
            <span>&copy; {new Date().getFullYear()} Wayfinder AI. Open source MIT license.</span>
            <div className="landing-footer__status">
              <span className="telemetry-pill__dot telemetry-pill__dot--green" />
              <span>All Systems Operational</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
