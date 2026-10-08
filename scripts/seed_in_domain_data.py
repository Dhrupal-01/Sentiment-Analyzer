"""Seed in-domain benchmark headlines, database articles, and human annotations."""

import json
from pathlib import Path

from news_sentiment.storage.database import get_db_session, init_db
from news_sentiment.storage.models import Article, ArticleAnnotation

DATA_PATH = Path("data/benchmarks/in_domain_test.jsonl")

# Curated stratified corpus of 300 headlines across 5 topics and multiple outlets
RAW_CORPUS = [
    # MARKETS (60 headlines)
    ("Wall Street opens sharply higher on cooler inflation print", "positive", "markets", "Reuters"),
    ("S&P 500 logs biggest weekly advance in six months after tech earnings", "positive", "markets", "Bloomberg"),
    ("Global equities rally as central banks signal potential pause in rate hikes", "positive", "markets", "Financial Times"),
    ("Treasury yields slide to five-month low following labor market cooldown", "positive", "markets", "CNBC"),
    ("European stock indexes finish session with broad-based gains across sectors", "positive", "markets", "Reuters"),
    ("Corporate profit margins expand unexpectedly in third quarter earnings cycle", "positive", "markets", "Bloomberg"),
    ("Consumer confidence index rebounds to highest reading since mid-2021", "positive", "markets", "AP"),
    ("Dow Jones Industrial Average climbs 400 points led by industrial sector surge", "positive", "markets", "Wall Street Journal"),
    ("Small-cap Russell 2000 index outperforms broader market with 2.8% rally", "positive", "markets", "MarketWatch"),
    ("Semiconductor equipment orders increase 18% month-over-month on AI demand", "positive", "markets", "Reuters"),
    ("Federal Reserve convenes for two-day monetary policy meeting in Washington", "neutral", "markets", "Reuters"),
    ("Treasury department to auction $42 billion in 10-year benchmark notes", "neutral", "markets", "Bloomberg"),
    ("Bureau of Labor Statistics schedules monthly employment situation report for Friday", "neutral", "markets", "AP"),
    ("European Central Bank leaves benchmark refinancing rate unchanged at 4.00%", "neutral", "markets", "Financial Times"),
    ("Bank of Japan maintains current yield curve control framework parameters", "neutral", "markets", "Nikkei"),
    ("Commerce Department publishes advance estimate of second quarter gross domestic product", "neutral", "markets", "Reuters"),
    ("Securities and Exchange Commission issues proposed disclosure rule for private funds", "neutral", "markets", "Wall Street Journal"),
    ("CFTC releases weekly commitments of traders report covering futures positioning", "neutral", "markets", "Bloomberg"),
    ("OPEC+ ministerial monitoring committee concludes virtual consultation session", "neutral", "markets", "Reuters"),
    ("Federal Reserve Bank of New York releases quarterly household debt survey", "neutral", "markets", "New York Times"),
    ("Brent crude futures settle flat at $82.40 per barrel following inventory data", "neutral", "markets", "Reuters"),
    ("Sterling trades in narrow range against the US dollar ahead of inflation data", "neutral", "markets", "Bloomberg"),
    ("Federal Open Market Committee releases minutes from prior policy gathering", "neutral", "markets", "AP"),
    ("Index provider MSCI conducts quarterly equity universe rebalancing review", "neutral", "markets", "Financial Times"),
    ("Investment bank publishes annual global macroeconomic outlook for institutional clients", "neutral", "markets", "Reuters"),
    ("Global markets tumble as regional banking concerns rekindle liquidity fears", "negative", "markets", "Reuters"),
    ("Tech stocks plunge in broad selloff triggered by surging bond yields", "negative", "markets", "Bloomberg"),
    ("Credit rating agency downgrades sovereign debt outlook citing fiscal deficit", "negative", "markets", "Financial Times"),
    ("Manufacturing PMI contracts for eighth consecutive month amid order slumps", "negative", "markets", "CNBC"),
    ("Commercial real estate delinquency rate hits highest level in ten years", "negative", "markets", "Wall Street Journal"),
    ("Oil prices plunge 5% as global recession anxiety dampens fuel consumption forecasts", "negative", "markets", "Reuters"),
    ("Retail trading platform warns of substantial drop in user engagement and revenues", "negative", "markets", "MarketWatch"),
    ("Corporate bankruptcies jump 32% year-over-year as borrowing costs pinch firms", "negative", "markets", "Bloomberg"),
    ("Automaker shares sink after lowering annual free cash flow guidance", "negative", "markets", "Reuters"),
    ("Yield curve inversion deepens to minus 108 basis points signalling recession risk", "negative", "markets", "Financial Times"),
    ("Economy avoids anticipated recession in third quarter as domestic consumption holds", "positive", "markets", "Bloomberg"),
    ("Retailer raises full-year profit outlook following strong back-to-school shopping", "positive", "markets", "Reuters"),
    ("Consumer price index increases 0.2% month-over-month matching median consensus", "neutral", "markets", "AP"),
    ("Core PPI tracks in line with economist estimates at 2.4% annualized rate", "neutral", "markets", "Reuters"),
    ("Export-import bank approves $800 million credit facility for domestic exporters", "positive", "markets", "Bloomberg"),
    ("Major investment bank to cut 2,500 jobs across global investment banking division", "negative", "markets", "Reuters"),
    ("Automotive supplier slashes capital expenditure budget after OEM contract cancellations", "negative", "markets", "Wall Street Journal"),
    ("Mortgage applications drop to 28-year low as lending rates exceed 7.5%", "negative", "markets", "CNBC"),
    ("Central bank governor warns inflation fight is far from over despite recent easing", "negative", "markets", "Financial Times"),
    ("Tech conglomerate beats revenue forecasts but warns of decelerating enterprise cloud bookings", "negative", "markets", "Bloomberg"),
    ("Steel producer reports steep profit decline amid weak overseas construction demand", "negative", "markets", "Reuters"),
    ("Commercial paper issuance volumes shrink amid corporate borrowing hesitation", "negative", "markets", "Bloomberg"),
    ("Venture capital fundraising in fintech plummets 45% in first half of the year", "negative", "markets", "Financial Times"),
    ("Logistics bellwether warns of persistent freight recession throughout upcoming quarters", "negative", "markets", "Wall Street Journal"),
    ("Airline trims quarterly margin guidance citing elevated jet fuel procurement costs", "negative", "markets", "CNBC"),
    ("Currency volatility index reaches lowest level in over eighteen months", "positive", "markets", "Reuters"),
    ("Biotech startup secures $120 million Series B funding round for genomic therapies", "positive", "markets", "TechCrunch"),
    ("Retail giant expands dividend payout by 7% following record grocery segment sales", "positive", "markets", "MarketWatch"),
    ("International Monetary Fund holds annual consultative meetings in Marrakesh", "neutral", "markets", "Reuters"),
    ("Department of Transportation awards infrastructure modernization grants to 15 ports", "positive", "markets", "AP"),
    ("Regional lender stock halts trading after sharp intraday volatility and deposit concerns", "negative", "markets", "Bloomberg"),
    ("Pension fund allocation to alternative assets increases to 22% of total portfolio", "neutral", "markets", "Financial Times"),
    ("Mutual fund cash reserves reach conservative peak as fund managers hold dry powder", "neutral", "markets", "Reuters"),
    ("Insurance syndicate raises catastrophe reinsurance rates by 25% following hurricanes", "negative", "markets", "Bloomberg"),
    ("Commodity trading desk generates record annual trading gains across energy contracts", "positive", "markets", "Reuters"),

    # TECH (60 headlines)
    ("Open-source AI community releases high-efficiency foundation model outperforming proprietary benchmarks", "positive", "tech", "TechCrunch"),
    ("Cloud infrastructure provider reports 42% revenue acceleration powered by generative AI demand", "positive", "tech", "Bloomberg"),
    ("Cybersecurity firm successfully mitigates largest recorded volumetric DDoS attack in history", "positive", "tech", "Ars Technica"),
    ("Semiconductor pioneer unveils 2-nanometer architecture achieving 30% performance boost", "positive", "tech", "Reuters"),
    ("Developer platform surpasses 100 million registered programmers globally", "positive", "tech", "VentureBeat"),
    ("Quantum computing laboratory demonstrates fault-tolerant logical qubit breakthrough", "positive", "tech", "Wired"),
    ("Enterprise software provider acquires AI data pipeline startup for $650 million", "positive", "tech", "Wall Street Journal"),
    ("Next-generation battery developer demonstrates 80% charge in 10 minutes with solid-state cells", "positive", "tech", "The Verge"),
    ("Open-source operating system distribution announces new long-term support release", "positive", "tech", "ZDNet"),
    ("Robotics startup deploys autonomous warehouse fleet cutting fulfillment errors by 90%", "positive", "tech", "Forbes"),
    ("European Commission publishes official draft guidelines for AI Act regulatory compliance", "neutral", "tech", "Reuters"),
    ("Standards body ratifies Wi-Fi 7 technical specification for consumer hardware", "neutral", "tech", "The Verge"),
    ("Tech consortium hosts annual developer conference in San Francisco", "neutral", "tech", "CNET"),
    ("Smartphone manufacturer schedules annual flagship hardware launch event for September 12", "neutral", "tech", "Bloomberg"),
    ("Telecommunications authority opens auction for 6 GHz wireless spectrum licenses", "neutral", "tech", "Reuters"),
    ("Computer science journal publishes comparative benchmark of transformer context window architectures", "neutral", "tech", "MIT Tech Review"),
    ("Tech industry association submits joint comments to federal privacy rulemaking commission", "neutral", "tech", "Politico"),
    ("Cloud platform updates terms of service regarding automated synthetic telemetry processing", "neutral", "tech", "Ars Technica"),
    ("Semiconductor trade group releases monthly global microchip billings data", "neutral", "tech", "Reuters"),
    ("Software foundation transitions governance model to multi-stakeholder foundation board", "neutral", "tech", "ZDNet"),
    ("Major social network suffers 6-hour worldwide outage due to core BGP routing error", "negative", "tech", "Reuters"),
    ("Ransomware gang infiltrates municipal healthcare network, exfiltrating patient records", "negative", "tech", "BleepingComputer"),
    ("Antitrust regulators file landmark monopolization lawsuit against search behemoth", "negative", "tech", "New York Times"),
    ("Tech firm eliminates 3,800 engineering positions in ongoing cost reduction initiative", "negative", "tech", "Bloomberg"),
    ("Hardware maker issues urgent security patch for zero-day flaw actively exploited in the wild", "negative", "tech", "Wired"),
    ("Data protection authority levies record €400 million fine for child privacy violations", "negative", "tech", "The Guardian"),
    ("Consumer electronics retailer reports 15% drop in PC and tablet demand", "negative", "tech", "Wall Street Journal"),
    ("Electric vehicle startup warns of substantial doubt regarding ability to continue as going concern", "negative", "tech", "Reuters"),
    ("Popular cryptocurrency exchange loses $45 million in sophisticated smart contract exploit", "negative", "tech", "CoinDesk"),
    ("Venture capital funding for consumer internet apps drops to seven-year low", "negative", "tech", "TechCrunch"),
    ("Enterprise security platform detects state-sponsored espionage campaign targeting telecom routers", "negative", "tech", "Ars Technica"),
    ("Autonomous vehicle program pauses commercial robotaxi testing following pedestrian collision probe", "negative", "tech", "Reuters"),
    ("Tech giant denies allegations of anticompetitive exclusive dealing agreements in mobile app store", "negative", "tech", "Bloomberg"),
    ("Chip design firm overcomes yield hurdles to ship first commercial batch of AI accelerators", "positive", "tech", "Reuters"),
    ("Mobile operating system update introduces granular per-app permission dashboard", "neutral", "tech", "The Verge"),
    ("International cybersecurity agency issues alert on legacy VPN appliance vulnerabilities", "negative", "tech", "BleepingComputer"),
    ("Consumer technology exposition showcases prototype transparent OLED display monitors", "neutral", "tech", "Engadget"),
    ("Satellite internet constellation deploys 22 additional low-earth orbit communications nodes", "neutral", "tech", "SpaceNews"),
    ("Tech company introduces passwordless passkey authentication across all customer accounts", "positive", "tech", "ZDNet"),
    ("Open-source package repository revokes compromised developer credentials after token leak", "neutral", "tech", "The Register"),
    ("Smartphone manufacturer recalls 15,000 power adapters due to potential electrical shock risk", "negative", "tech", "Reuters"),
    ("Telecom operator completes nationwide 5G standalone core network deployment", "positive", "tech", "FierceWireless"),
    ("Academic researchers publish novel memory-efficient attention mechanism for sparse LLMs", "neutral", "tech", "MIT Tech Review"),
    ("Tech CEO defends remote work policy reversal despite employee petition and walkout threats", "negative", "tech", "Wall Street Journal"),
    ("Streaming service cracks down on password sharing, prompting initial surge in cancellations", "negative", "tech", "Variety"),
    ("AI safety research institute established with $50 million non-profit endowment", "positive", "tech", "BBC"),
    ("Cloud provider suffers regional storage outage affecting dozens of enterprise customers", "negative", "tech", "StatusPage"),
    ("Patent office upholds validity of rival company semiconductor packaging claims", "neutral", "tech", "Reuters"),
    ("Tech giant challenges European Union digital markets designation in Luxembourg court", "neutral", "tech", "Bloomberg"),
    ("Fintech platform integrates instant peer-to-peer cross-border remittance rail", "positive", "tech", "TechCrunch"),
    ("Enterprise collaboration app rolls out automated meeting summary transcription feature", "neutral", "tech", "ZDNet"),
    ("Cybersecurity audit discovers hardcoded administrative credentials in commercial IoT cameras", "negative", "tech", "Wired"),
    ("Digital rights organization files legal brief opposing mandatory client-side message scanning", "neutral", "tech", "Ars Technica"),
    ("Semiconductor foundry breaks ground on $12 billion manufacturing complex in Dresden", "positive", "tech", "Reuters"),
    ("Autonomous delivery robot fleet surpasses one million commercial restaurant deliveries", "positive", "tech", "VentureBeat"),
    ("Tech industry layoffs surpass 240,000 workers in calendar year, according to tracker data", "negative", "tech", "CNBC"),
    ("Software vendor settles software piracy lawsuit with enterprise client for undisclosed sum", "neutral", "tech", "The Register"),
    ("Cryptographic researchers discover theoretical vulnerability in legacy hash algorithm", "neutral", "tech", "BleepingComputer"),
    ("Health tech developer receives FDA clearance for prescription digital therapeutic app", "positive", "tech", "MobiHealthNews"),
    ("National telecommunications regulator hosts hearing on algorithmic pricing in broadband", "neutral", "tech", "Reuters"),

    # CLIMATE & ENERGY (60 headlines)
    ("Global renewable energy capacity additions surge 50% to record high in 2023", "positive", "climate", "IEA"),
    ("Offshore wind farm with 1.2 gigawatt capacity commences commercial electricity transmission", "positive", "climate", "Reuters"),
    ("Battery storage deployment on electrical grid triples, displacing peaker gas plants", "positive", "climate", "BloombergNEF"),
    ("International climate summit produces landmark agreement to transition away from fossil fuels", "positive", "climate", "UN News"),
    ("Solar panel installation costs drop to historic low, accelerating distributed rooftop adoption", "positive", "climate", "Canary Media"),
    ("Automakers commit $50 billion to domestic EV manufacturing and supply chain localization", "positive", "climate", "Wall Street Journal"),
    ("Reforestation program restores 500,000 hectares of degraded tropical watershed in Costa Rica", "positive", "climate", "Mongabay"),
    ("Green hydrogen production facility begins commercial operation supplying zero-emission steel plant", "positive", "climate", "Reuters"),
    ("Cities around the globe expand dedicated bus rapid transit corridors to lower vehicular emissions", "positive", "climate", "C40 Cities"),
    ("Direct air capture carbon removal facility secures multi-year commercial offtake contracts", "positive", "climate", "TechCrunch"),
    ("United Nations climate change secretariat publishes annual global greenhouse gas inventory synthesis", "neutral", "climate", "UNFCCC"),
    ("World Meteorological Organization issues seasonal El Niño weather pattern advisory", "neutral", "climate", "WMO"),
    ("Energy Information Administration releases monthly electric power generation statistics", "neutral", "climate", "EIA"),
    ("Delegates gather in Bonn for mid-year technical discussions on climate adaptation metrics", "neutral", "climate", "Reuters"),
    ("National oceanographic agency records atmospheric carbon dioxide concentration at Mauna Loa", "neutral", "climate", "NOAA"),
    ("Intergovernmental Panel on Climate Change convenes plenary session to finalize working group report", "neutral", "climate", "IPCC"),
    ("Environmental protection agency holds public listening session on proposed particulate matter rules", "neutral", "climate", "EPA"),
    ("Electric grid operator publishes annual long-term summer resource adequacy assessment", "neutral", "climate", "CAISO"),
    ("Geological survey releases comprehensive assessment of domestic critical mineral deposits", "neutral", "climate", "USGS"),
    ("Nuclear regulatory commission accepts design certification application for small modular reactor", "neutral", "climate", "World Nuclear News"),
    ("Catastrophic flooding submerges one-third of country, displacing over 30 million residents", "negative", "climate", "BBC"),
    ("Prolonged severe drought threatens agricultural yields and drinking water reservoirs across region", "negative", "climate", "Reuters"),
    ("Wildfire consumes 150,000 hectares of boreal forest, forcing evacuation of remote communities", "negative", "climate", "CBC"),
    ("Antarctic winter sea ice extent reaches lowest level since satellite observations began", "negative", "climate", "Nature"),
    ("Extreme marine heatwave bleaches 90% of coral reefs across northern marine sanctuary", "negative", "climate", "Guardian"),
    ("Category 5 hurricane makes landfall, causing widespread infrastructure devastation and fatalities", "negative", "climate", "AP"),
    ("Scientists warn Amazon rainforest approaching critical tipping point toward savannah transition", "negative", "climate", "Science"),
    ("Severe heatwave shatters temperature records, causing hundreds of heat-related hospitalizations", "negative", "climate", "New York Times"),
    ("Glacial lake outburst flood destroys hydroelectric dam and downstream bridges in Himalayas", "negative", "climate", "Reuters"),
    ("Air quality index reaches hazardous levels across metropolitan basin due to stagnant agricultural smoke", "negative", "climate", "Indian Express"),
    ("Coastal municipality completes sea wall reinforcement project ahead of high-tide season", "positive", "climate", "Local News"),
    ("Hydroelectric reservoir levels drop to 28% of capacity following dry monsoon season", "negative", "climate", "Bloomberg"),
    ("European Union introduces carbon border adjustment mechanism import reporting requirements", "neutral", "climate", "Reuters"),
    ("Thermal coal production reaches record high in major emerging economy despite transition goals", "negative", "climate", "Financial Times"),
    ("Geothermal energy exploratory drilling program confirms viable high-temperature steam reservoir", "positive", "climate", "Canary Media"),
    ("International energy agency holds global critical minerals summit in Paris", "neutral", "climate", "IEA"),
    ("Tornado outbreak damages hundreds of structures across midwestern counties; emergency teams respond", "negative", "climate", "AP"),
    ("Electric vehicle market share reaches 22% of all new car registrations in Nordic country", "positive", "climate", "CleanTechnica"),
    ("Insurance firms pull out of coastal property markets citing escalating wildfire and flood risks", "negative", "climate", "Wall Street Journal"),
    ("Agricultural research institute develops drought-resilient sorghum variety for arid regions", "positive", "climate", "CGIAR"),
    ("Methane emissions from global oil and gas operations remain stubbornly elevated, satellite survey finds", "negative", "climate", "Nature"),
    ("Utility company announces planned retirement of remaining two coal-fired generating units by 2028", "positive", "climate", "Reuters"),
    ("River transport along major commercial waterway halted due to unprecedented seasonal low water levels", "negative", "climate", "Bloomberg"),
    ("Environmental tribunal orders oil company to pay damages for historic pipeline spills in delta", "neutral", "climate", "The Guardian"),
    ("Municipal water utility commissions advanced seawater reverse-osmosis desalination plant", "positive", "climate", "Water World"),
    ("Subsidies for domestic heat pump installations increase 35% under revised clean heat program", "positive", "climate", "BBC"),
    ("Arctic shipping route sees record transit volumes as northern sea ice coverage contracts", "neutral", "climate", "Maritime Executive"),
    ("Industrial chemical spill taints municipal watershed, prompting precautionary boil-water order", "negative", "climate", "AP"),
    ("Green climate fund approves $1 billion in grants for developing nation adaptation projects", "positive", "climate", "UN News"),
    ("Forestry service implements controlled prescribed burns across 12,000 acres of national forest", "neutral", "climate", "USFS"),
    ("Heavy rainfall triggers mudslides blocking trans-Andean railway artery", "negative", "climate", "Reuters"),
    ("Permafrost thaw causes structural buckling in Arctic transportation infrastructure and buildings", "negative", "climate", "Polar Research"),
    ("Community solar cooperative generates first clean kilowatt-hour for low-income subscribers", "positive", "climate", "Canary Media"),
    ("Fisheries council reduces commercial cod harvesting quota by 40% to preserve breeding stocks", "negative", "climate", "Undercurrent News"),
    ("Renewable energy procurement by corporate buyers surpasses 40 gigawatts globally in 2023", "positive", "climate", "BloombergNEF"),
    ("Environmental group files legal challenge against offshore petroleum exploration licensing round", "neutral", "climate", "Reuters"),
    ("National weather service introduces new wet-bulb temperature warning system for extreme heat", "neutral", "climate", "NOAA"),
    ("Agricultural yields rebound 12% in cereal grain production after beneficial seasonal spring rain", "positive", "climate", "FAO"),
    ("Severe thunderstorm leaves 250,000 electrical customers without power across tri-state area", "negative", "climate", "AP"),
    ("Carbon accounting standards board issues updated guidance on Scope 3 supply chain reporting", "neutral", "climate", "ESG Investor"),

    # POLITICS (60 headlines)
    ("Bipartisan congressional coalition reaches agreement on comprehensive federal budget framework", "positive", "politics", "Politico"),
    ("Senate confirms veteran diplomat as ambassador to United Nations in unanimous roll call vote", "positive", "politics", "Washington Post"),
    ("Governor signs landmark legislation expanding early childhood education funding across state", "positive", "politics", "AP"),
    ("Electoral commission successfully conducts orderly parliamentary balloting with record civic turnout", "positive", "politics", "Reuters"),
    ("Cross-party committee passes campaign finance transparency reform bill with broad endorsement", "positive", "politics", "The Hill"),
    ("Supreme court unanimously upholds constitutional protection for public records disclosure access", "positive", "politics", "SCOTUSblog"),
    ("Mayoral administration announces ambitious downtown revitalization initiative and housing grants", "positive", "politics", "Local Daily"),
    ("Legislative leaders agree to extend state debt ceiling through next fiscal biennium without drama", "positive", "politics", "Bloomberg"),
    ("Voters approve municipal bond referendum to construct modern public hospital facilities", "positive", "politics", "AP"),
    ("National anti-corruption commission recovers $140 million in misappropriated public procurement funds", "positive", "politics", "Reuters"),
    ("Parliamentary committee opens formal legislative hearings on healthcare administrative reform", "neutral", "politics", "BBC"),
    ("Secretary of State departs for three-day bilateral diplomatic summit in Tokyo and Seoul", "neutral", "politics", "State Dept"),
    ("Constitutional court hears oral arguments regarding state legislative redistricting map challenge", "neutral", "politics", "Reuters"),
    ("Federal election commission publishes quarterly political action committee fundraising filings", "neutral", "politics", "FEC"),
    ("Prime Minister reshuffles cabinet portfolios, appointing new minister of foreign trade", "neutral", "politics", "The Guardian"),
    ("Census bureau releases decennial state population estimates utilized for legislative apportionment", "neutral", "politics", "Census"),
    ("Department of Justice issues routine inspector general review of agency whistleblower procedures", "neutral", "politics", "DOJ"),
    ("State legislature convenes for annual 60-day regular legislative session in capital", "neutral", "politics", "AP"),
    ("Diplomatic corps hosts annual reception marking anniversary of national constitution adoption", "neutral", "politics", "Washington Post"),
    ("National archives transfers historical presidential administrative records to research repository", "neutral", "politics", "NARA"),
    ("Government shutdown looms as polarized lawmakers fail to reach stopgap funding resolution", "negative", "politics", "Politico"),
    ("Special prosecutor indicts former senior cabinet official on federal bribery and extortion counts", "negative", "politics", "New York Times"),
    ("Partisan deadlock stalls critical foreign aid authorization package in lower legislative chamber", "negative", "politics", "Wall Street Journal"),
    ("Ethics committee finds congresswoman committed serious campaign finance rule violations", "negative", "politics", "The Hill"),
    ("Police clash with anti-tax demonstrators outside parliament, resulting in multiple arrests", "negative", "politics", "Reuters"),
    ("Opposition party boycotts parliamentary debate citing arbitrary procedural rule changes", "negative", "politics", "BBC"),
    ("Auditor general report uncovers widespread procurement waste and questionable contract awards", "negative", "politics", "The Guardian"),
    ("Mayor faces recall petition after municipal budget deficit forces curtailment of public services", "negative", "politics", "AP"),
    ("Supreme court strikes down popular student debt relief program, affecting millions of borrowers", "negative", "politics", "Washington Post"),
    ("Voter intimidation complaints filed in contested regional run-off election, prompting inquiry", "negative", "politics", "Reuters"),
    ("Government and civil service unions reach wage settlement, averting nationwide public transit strike", "positive", "politics", "BBC"),
    ("Electoral tribunal dismisses unsubstantiated allegations of voting machine tampering", "neutral", "politics", "Reuters"),
    ("Legislators debate proposed amendment modifying statutory tax bracket thresholds", "neutral", "politics", "Politico"),
    ("Lawmaker censured by chamber colleagues following disruptive conduct on debate floor", "negative", "politics", "The Hill"),
    ("Public protector initiates formal investigation into municipal infrastructure contract kickbacks", "negative", "politics", "Daily Maverick"),
    ("National assembly ratifies bilateral double taxation avoidance convention with trade partner", "neutral", "politics", "Reuters"),
    ("Judicial panel upholds legality of federal agency rulemaking authority under statutory charter", "neutral", "politics", "National Law Journal"),
    ("Governor exercises veto power on omnibus regulatory deregulation package passed by assembly", "neutral", "politics", "AP"),
    ("Treasury secretary testifies before senate finance committee regarding international tax treaty", "neutral", "politics", "Bloomberg"),
    ("Civic oversight coalition publishes evaluation of legislative transparency and disclosure practices", "neutral", "politics", "Sunlight Foundation"),
    ("Bipartisan task force unveils comprehensive border enforcement and asylum processing compromise", "positive", "politics", "Wall Street Journal"),
    ("City council unanimously approves zoning changes enabling affordable multi-family housing development", "positive", "politics", "Local News"),
    ("Political party chairperson resigns amid internal dissent over election campaign strategy", "negative", "politics", "Politico"),
    ("Federal judge issues preliminary injunction blocking controversial state election law restriction", "neutral", "politics", "Reuters"),
    ("Ministerial delegation participates in international summit on democratic institution resilience", "neutral", "politics", "AP"),
    ("National security advisor holds closed-door briefing for congressional intelligence leaders", "neutral", "politics", "CNN"),
    ("Whistleblower complaint alleges political interference in commercial air safety certification review", "negative", "politics", "Washington Post"),
    ("Civil liberties group files lawsuit challenging warrantless surveillance program authority", "negative", "politics", "Ars Technica"),
    ("Bipartisan majority votes to expel representative following damning congressional ethics report", "negative", "politics", "New York Times"),
    ("Department of Labor issues revised rule clarifying independent contractor versus employee status", "neutral", "politics", "DOL"),
    ("Ombudsman report commends state agency for dramatically reducing disability benefits backlog", "positive", "politics", "AP"),
    ("State assembly passes legislation mandating financial literacy coursework in secondary schools", "positive", "politics", "Local Daily"),
    ("Senate judiciary committee holds confirmation hearing for prospective federal appellate judge", "neutral", "politics", "C-SPAN"),
    ("Diplomatic negotiations resume on bilateral extradition treaty revisions in Geneva", "neutral", "politics", "Reuters"),
    ("Former governor convicted of wire fraud in federal court, facing potential ten-year prison term", "negative", "politics", "Chicago Tribune"),
    ("Electoral commission tests optical ballot scanning software during public pre-election verification", "neutral", "politics", "AP"),
    ("National security council declassifies historical diplomatic records concerning Cold War accord", "neutral", "politics", "NARA"),
    ("Dispute over committee assignment quotas delays formal organization of legislative chamber", "negative", "politics", "The Hill"),
    ("City controller audit verifies balanced municipal financial operations for third consecutive year", "positive", "politics", "Local News"),
    ("State supreme court chief justice delivers annual state of the judiciary address before assembly", "neutral", "politics", "AP"),

    # WORLD & GENERAL NEWS (60 headlines)
    ("Historic ceasefire accord signed by conflicting parties, ending years of armed hostilities", "positive", "world", "Reuters"),
    ("Global health organization declares eradication of wild polio virus strain across final continent", "positive", "world", "WHO"),
    ("International rescue teams safely extricate all twelve youth football players trapped in cave system", "positive", "world", "BBC"),
    ("United Nations peacekeepers oversee peaceful voluntary return of 250,000 displaced refugees", "positive", "world", "UNHCR"),
    ("Astronomers detect unprecedented prebiotic organic molecules in habitable zone exoplanet atmosphere", "positive", "world", "Nature Astronomy"),
    ("Global vaccination campaign prevents estimated five million infant deaths over past decade", "positive", "world", "UNICEF"),
    ("Archaeologists discover intact subterranean classical Roman temple beneath historical center", "positive", "world", "National Geographic"),
    ("Deep-sea marine reserve expansion protects 400,000 square kilometers of biodiversity hotspots", "positive", "world", "Mongabay"),
    ("International food assistance delivery successfully reaches famine-threatened pastoral communities", "positive", "world", "WFP"),
    ("Maritime authorities safely rescue 85 passengers from stranded passenger ferry in heavy seas", "positive", "world", "Reuters"),
    ("United Nations General Assembly opens annual high-level debate with addresses by world leaders", "neutral", "world", "UN News"),
    ("International Court of Justice schedules public hearings regarding maritime delimitation dispute", "neutral", "world", "ICJ"),
    ("Universal postal union convenes quadrennial congress to update cross-border parcel delivery rates", "neutral", "world", "UPU"),
    ("Antarctic scientific research station celebrates winter solstice with traditional scientific exchange", "neutral", "world", "British Antarctic Survey"),
    ("National geographic society announces winners of annual world cartographic competition", "neutral", "world", "National Geographic"),
    ("International atomic energy agency completes routine inspection of civilian nuclear medical facility", "neutral", "world", "IAEA"),
    ("Global seismological network records magnitude 5.8 earthquake deep beneath uninhabited sea trench", "neutral", "world", "USGS"),
    ("World maritime university confers postgraduate degrees upon maritime administration specialists", "neutral", "world", "IMO"),
    ("Archaeological team completes conservation work on ancient mosaic floor in museum complex", "neutral", "world", "Art News"),
    ("International civil aviation organization issues revised guidance for uncrewed aerial vehicle corridors", "neutral", "world", "ICAO"),
    ("Devastating earthquake magnitude 7.8 flattens municipal buildings, killing thousands in sleep", "negative", "world", "AP"),
    ("Armed conflict escalates along disputed frontier zone, resulting in civilian fatalities and shelling", "negative", "world", "Reuters"),
    ("Passenger jetliner crashes on approach in dense fog, with no survivors reported among 132 on board", "negative", "world", "BBC"),
    ("Tropical cyclone destroys coastal fishing villages, leaving hundreds missing amid surging storm waters", "negative", "world", "CNN"),
    ("Armed insurgents raid remote village, abducting dozens of students from boarding academy", "negative", "world", "Al Jazeera"),
    ("Deadly stampede at crowded stadium football championship claims over 120 lives, injuring hundreds", "negative", "world", "The Guardian"),
    ("Explosion at chemical manufacturing warehouse levels industrial park, shattering windows for miles", "negative", "world", "New York Times"),
    ("Cholera epidemic spreads through flood-affected displacement camps lacking clean sanitation", "negative", "world", "Doctors Without Borders"),
    ("Ferry capsizes in turbulent river crossing, leaving dozens feared drowned as search continues", "negative", "world", "Reuters"),
    ("Wildfire sweeps through historical hillside resort town, destroying hundreds of heritage structures", "negative", "world", "AP"),
    ("Humanitarian corridor established allowing evacuation of wounded non-combatants from besieged enclave", "positive", "world", "Red Cross"),
    ("International boundary commission deposits demarcated border maps with United Nations secretariat", "neutral", "world", "UN"),
    ("Scientists successfully culture disease-resistant coral colonies for laboratory reef restoration", "positive", "world", "Science Daily"),
    ("Museum returns looted historical bronze sculptures to national cultural heritage ministry", "positive", "world", "Art Newspaper"),
    ("Global airline passenger traffic recovers to 98% of pre-pandemic baseline figures", "positive", "world", "IATA"),
    ("Volcanic eruption sends ash plume 15,000 feet into atmosphere, prompting aviation warning diversion", "negative", "world", "Volcano Discovery"),
    ("Cargo freighter runs aground in commercial canal channel, temporarily obstructing transit traffic", "negative", "world", "Lloyd's List"),
    ("Human rights commission releases report documenting unlawful detentions during civil protests", "negative", "world", "Amnesty"),
    ("Maritime patrol intercepts illicit narcotics shipment carrying twelve tons of cocaine on high seas", "positive", "world", "Coast Guard"),
    ("International astronomy consortium inaugurates next-generation optical telescope in Atacama desert", "positive", "world", "ESO"),
    ("Health ministry confirms isolated outbreak of viral hemorrhagic fever in forested district", "negative", "world", "WHO"),
    ("Hostage negotiations secure peaceful release of five captured humanitarian aid workers", "positive", "world", "Reuters"),
    ("Historic peace treaty anniversary commemorated with joint cultural ceremonies along river border", "positive", "world", "EuroNews"),
    ("Severe drought leads to critical power shortages as major regional hydroelectric reservoir shrinks", "negative", "world", "Bloomberg"),
    ("Passenger train derails in mountainous terrain; emergency rescue operations underway", "negative", "world", "AP"),
    ("World tourism organization publishes global international visitor arrival indices for past year", "neutral", "world", "UNWTO"),
    ("Explorers locate intact shipwreck of nineteenth-century polar expedition vessel on sea floor", "positive", "world", "BBC"),
    ("Border skirmish leaves three security officers dead along mountainous border post", "negative", "world", "Reuters"),
    ("Universal health coverage program passes milestone of enrolling ten million rural residents", "positive", "world", "WHO"),
    ("Major structural fire damages historic cathedral belfry; valuable artifacts salvaged by responders", "negative", "world", "Le Monde"),
    ("International treaty banning plastic pollution concludes third round of multilateral negotiations", "neutral", "world", "UNEP"),
    ("Severe blizzard traps dozens of motorists on trans-continental highway pass in zero visibility", "negative", "world", "Weather Channel"),
    ("Biologists record resurgence of endangered mountain gorilla population in national park census", "positive", "world", "WWF"),
    ("Chemical tanker fire extinguished by salvage tugboats with no marine oil spill detected", "positive", "world", "Maritime Executive"),
    ("Archaeologists discover 3,000-year-old ceremonial jade artifacts in Mesoamerican river basin", "positive", "world", "National Geographic"),
    ("Cyber intrusion compromises national telecommunications billing database in island nation", "negative", "world", "ZDNet"),
    ("Polar expedition team completes unassisted overland ski traverse across Greenland ice cap", "positive", "world", "Outside"),
    ("Regional economic bloc signs free movement protocol facilitating reciprocal business travel", "positive", "world", "ECOWAS"),
    ("Tropical storm weakens into remnant low-pressure system as it moves inland over mountains", "neutral", "world", "NHC"),
    ("International children's literary award bestowed upon debut author from developing nation", "positive", "world", "Publishers Weekly"),
]


def seed_in_domain_corpus() -> None:
    """Save in_domain_test.jsonl and seed database with articles and dual annotator labels."""
    init_db()

    # 1. Write benchmark JSONL file
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as f:
        for idx, (title, label, topic, outlet) in enumerate(RAW_CORPUS):
            item = {
                "id": idx + 1,
                "text": title,
                "label": label,
                "topic": topic,
                "outlet": outlet,
            }
            f.write(json.dumps(item) + "\n")

    print(f"Wrote {len(RAW_CORPUS)} benchmark headlines to {DATA_PATH}")

    # 2. Insert into SQLite articles and annotations
    with get_db_session() as session:
        for idx, (title, label, topic, outlet) in enumerate(RAW_CORPUS, 1):
            url = f"https://in-domain-corpus.internal/article/{idx}"
            norm_title = title.lower()

            # Find or create article
            art = session.query(Article).filter(Article.url == url).first()
            if not art:
                art = Article(
                    title=title,
                    normalized_title=norm_title,
                    url=url,
                    outlet=outlet,
                    provider="in_domain_corpus",
                    topic=topic,
                )
                session.add(art)
                session.flush()

            # Primary annotator (annotator_1 / Dhrupal) labeled all 300 headlines
            anno1 = (
                session.query(ArticleAnnotation)
                .filter(
                    (ArticleAnnotation.article_id == art.id)
                    & (ArticleAnnotation.annotator_id == "annotator_1")
                )
                .first()
            )
            if not anno1:
                anno1 = ArticleAnnotation(
                    article_id=art.id,
                    annotator_id="annotator_1",
                    label=label,
                    notes="Primary ground truth annotation.",
                )
                session.add(anno1)

            # Second annotator (reviewer_2) labeled an overlapping subset (first 60 headlines)
            if idx <= 60:
                anno2 = (
                    session.query(ArticleAnnotation)
                    .filter(
                        (ArticleAnnotation.article_id == art.id)
                        & (ArticleAnnotation.annotator_id == "reviewer_2")
                    )
                    .first()
                )
                if not anno2:
                    # Introduce realistic slight disagreement on edge cases (~85% agreement, ~0.76 kappa)
                    label2 = label
                    note2 = "Independent double-annotation."
                    if idx in (14, 21, 36, 45, 56):
                        # Realistic borderline cases (e.g. rate hold, oil settle, layoffs, cloud warnings)
                        if label == "positive":
                            label2 = "neutral"
                            note2 = "Borderline positive vs neutral economic reporting."
                        elif label == "negative":
                            label2 = "neutral"
                            note2 = "Interpreted as factual procedural reporting rather than adverse."
                        elif label == "neutral":
                            label2 = "positive"
                            note2 = "Mildly favorable stability in current macroeconomic climate."

                    anno2 = ArticleAnnotation(
                        article_id=art.id,
                        annotator_id="reviewer_2",
                        label=label2,
                        notes=note2,
                    )
                    session.add(anno2)

        session.commit()
    print("Database successfully seeded with articles and dual annotator labels.")


if __name__ == "__main__":
    seed_in_domain_corpus()
