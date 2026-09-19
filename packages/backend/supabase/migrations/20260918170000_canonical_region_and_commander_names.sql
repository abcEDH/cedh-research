-- Exact aliases: full region names are stored; existing uppercase region keys remain supported.
CREATE TABLE public.region_name_aliases (
  country_key text NOT NULL,
  alias text NOT NULL,
  canonical_name text NOT NULL,
  PRIMARY KEY (country_key, alias)
);
ALTER TABLE public.region_name_aliases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON public.region_name_aliases FOR SELECT USING (true);
CREATE POLICY "Service role write access" ON public.region_name_aliases FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.region_name_aliases TO anon, authenticated;
GRANT ALL ON public.region_name_aliases TO service_role;
INSERT INTO public.region_name_aliases (country_key, alias, canonical_name) VALUES
  ('UNITED STATES', 'ALABAMA', 'Alabama'),
  ('UNITED STATES', 'AL', 'Alabama'),
  ('UNITED STATES', 'ALASKA', 'Alaska'),
  ('UNITED STATES', 'AK', 'Alaska'),
  ('UNITED STATES', 'ARIZONA', 'Arizona'),
  ('UNITED STATES', 'AZ', 'Arizona'),
  ('UNITED STATES', 'ARKANSAS', 'Arkansas'),
  ('UNITED STATES', 'AR', 'Arkansas'),
  ('UNITED STATES', 'CALIFORNIA', 'California'),
  ('UNITED STATES', 'CA', 'California'),
  ('UNITED STATES', 'COLORADO', 'Colorado'),
  ('UNITED STATES', 'CO', 'Colorado'),
  ('UNITED STATES', 'CONNECTICUT', 'Connecticut'),
  ('UNITED STATES', 'CT', 'Connecticut'),
  ('UNITED STATES', 'DELAWARE', 'Delaware'),
  ('UNITED STATES', 'DE', 'Delaware'),
  ('UNITED STATES', 'DISTRICT OF COLUMBIA', 'District of Columbia'),
  ('UNITED STATES', 'DC', 'District of Columbia'),
  ('UNITED STATES', 'D.C.', 'District of Columbia'),
  ('UNITED STATES', 'D.C', 'District of Columbia'),
  ('UNITED STATES', 'D.C., US', 'District of Columbia'),
  ('UNITED STATES', 'FLORIDA', 'Florida'),
  ('UNITED STATES', 'FL', 'Florida'),
  ('UNITED STATES', 'GEORGIA', 'Georgia'),
  ('UNITED STATES', 'GA', 'Georgia'),
  ('UNITED STATES', 'HAWAII', 'Hawaii'),
  ('UNITED STATES', 'HI', 'Hawaii'),
  ('UNITED STATES', 'IDAHO', 'Idaho'),
  ('UNITED STATES', 'ID', 'Idaho'),
  ('UNITED STATES', 'ILLINOIS', 'Illinois'),
  ('UNITED STATES', 'IL', 'Illinois'),
  ('UNITED STATES', 'INDIANA', 'Indiana'),
  ('UNITED STATES', 'IN', 'Indiana'),
  ('UNITED STATES', 'IOWA', 'Iowa'),
  ('UNITED STATES', 'IA', 'Iowa'),
  ('UNITED STATES', 'KANSAS', 'Kansas'),
  ('UNITED STATES', 'KS', 'Kansas'),
  ('UNITED STATES', 'KENTUCKY', 'Kentucky'),
  ('UNITED STATES', 'KY', 'Kentucky'),
  ('UNITED STATES', 'LOUISIANA', 'Louisiana'),
  ('UNITED STATES', 'LA', 'Louisiana'),
  ('UNITED STATES', 'MAINE', 'Maine'),
  ('UNITED STATES', 'ME', 'Maine'),
  ('UNITED STATES', 'MARYLAND', 'Maryland'),
  ('UNITED STATES', 'MD', 'Maryland'),
  ('UNITED STATES', 'MASSACHUSETTS', 'Massachusetts'),
  ('UNITED STATES', 'MA', 'Massachusetts'),
  ('UNITED STATES', 'MICHIGAN', 'Michigan'),
  ('UNITED STATES', 'MI', 'Michigan'),
  ('UNITED STATES', 'MINNESOTA', 'Minnesota'),
  ('UNITED STATES', 'MN', 'Minnesota'),
  ('UNITED STATES', 'MISSISSIPPI', 'Mississippi'),
  ('UNITED STATES', 'MS', 'Mississippi'),
  ('UNITED STATES', 'MISSOURI', 'Missouri'),
  ('UNITED STATES', 'MO', 'Missouri'),
  ('UNITED STATES', 'MONTANA', 'Montana'),
  ('UNITED STATES', 'MT', 'Montana'),
  ('UNITED STATES', 'NEBRASKA', 'Nebraska'),
  ('UNITED STATES', 'NE', 'Nebraska'),
  ('UNITED STATES', 'NEVADA', 'Nevada'),
  ('UNITED STATES', 'NV', 'Nevada'),
  ('UNITED STATES', 'NEW HAMPSHIRE', 'New Hampshire'),
  ('UNITED STATES', 'NH', 'New Hampshire'),
  ('UNITED STATES', 'NEW JERSEY', 'New Jersey'),
  ('UNITED STATES', 'NJ', 'New Jersey'),
  ('UNITED STATES', 'NEW MEXICO', 'New Mexico'),
  ('UNITED STATES', 'NM', 'New Mexico'),
  ('UNITED STATES', 'NEW YORK', 'New York'),
  ('UNITED STATES', 'NY', 'New York'),
  ('UNITED STATES', 'NORTH CAROLINA', 'North Carolina'),
  ('UNITED STATES', 'NC', 'North Carolina'),
  ('UNITED STATES', 'NORTH DAKOTA', 'North Dakota'),
  ('UNITED STATES', 'ND', 'North Dakota'),
  ('UNITED STATES', 'OHIO', 'Ohio'),
  ('UNITED STATES', 'OH', 'Ohio'),
  ('UNITED STATES', 'OKLAHOMA', 'Oklahoma'),
  ('UNITED STATES', 'OK', 'Oklahoma'),
  ('UNITED STATES', 'OREGON', 'Oregon'),
  ('UNITED STATES', 'OR', 'Oregon'),
  ('UNITED STATES', 'PENNSYLVANIA', 'Pennsylvania'),
  ('UNITED STATES', 'PA', 'Pennsylvania'),
  ('UNITED STATES', 'RHODE ISLAND', 'Rhode Island'),
  ('UNITED STATES', 'RI', 'Rhode Island'),
  ('UNITED STATES', 'SOUTH CAROLINA', 'South Carolina'),
  ('UNITED STATES', 'SC', 'South Carolina'),
  ('UNITED STATES', 'SOUTH DAKOTA', 'South Dakota'),
  ('UNITED STATES', 'SD', 'South Dakota'),
  ('UNITED STATES', 'TENNESSEE', 'Tennessee'),
  ('UNITED STATES', 'TN', 'Tennessee'),
  ('UNITED STATES', 'TEXAS', 'Texas'),
  ('UNITED STATES', 'TX', 'Texas'),
  ('UNITED STATES', 'UTAH', 'Utah'),
  ('UNITED STATES', 'UT', 'Utah'),
  ('UNITED STATES', 'VERMONT', 'Vermont'),
  ('UNITED STATES', 'VT', 'Vermont'),
  ('UNITED STATES', 'VIRGINIA', 'Virginia'),
  ('UNITED STATES', 'VA', 'Virginia'),
  ('UNITED STATES', 'WASHINGTON', 'Washington'),
  ('UNITED STATES', 'WA', 'Washington'),
  ('UNITED STATES', 'WEST VIRGINIA', 'West Virginia'),
  ('UNITED STATES', 'WV', 'West Virginia'),
  ('UNITED STATES', 'WISCONSIN', 'Wisconsin'),
  ('UNITED STATES', 'WI', 'Wisconsin'),
  ('UNITED STATES', 'WYOMING', 'Wyoming'),
  ('UNITED STATES', 'WY', 'Wyoming'),
  ('UNITED STATES', 'PUERTO RICO', 'Puerto Rico'),
  ('UNITED STATES', 'PR', 'Puerto Rico'),
  ('UNITED STATES', 'GUAM', 'Guam'),
  ('UNITED STATES', 'GU', 'Guam'),
  ('UNITED STATES', 'UNITED STATES VIRGIN ISLANDS', 'United States Virgin Islands'),
  ('UNITED STATES', 'VI', 'United States Virgin Islands'),
  ('UNITED STATES', 'AMERICAN SAMOA', 'American Samoa'),
  ('UNITED STATES', 'AS', 'American Samoa'),
  ('UNITED STATES', 'NORTHERN MARIANA ISLANDS', 'Northern Mariana Islands'),
  ('UNITED STATES', 'MP', 'Northern Mariana Islands'),
  ('CANADA', 'ALBERTA', 'Alberta'),
  ('CANADA', 'AB', 'Alberta'),
  ('CANADA', 'BRITISH COLUMBIA', 'British Columbia'),
  ('CANADA', 'BC', 'British Columbia'),
  ('CANADA', 'MANITOBA', 'Manitoba'),
  ('CANADA', 'MB', 'Manitoba'),
  ('CANADA', 'NEW BRUNSWICK', 'New Brunswick'),
  ('CANADA', 'NB', 'New Brunswick'),
  ('CANADA', 'NOUVEAU BRUNSWICK', 'New Brunswick'),
  ('CANADA', 'NEWFOUNDLAND AND LABRADOR', 'Newfoundland and Labrador'),
  ('CANADA', 'NL', 'Newfoundland and Labrador'),
  ('CANADA', 'NOVA SCOTIA', 'Nova Scotia'),
  ('CANADA', 'NS', 'Nova Scotia'),
  ('CANADA', 'NORTHWEST TERRITORIES', 'Northwest Territories'),
  ('CANADA', 'NT', 'Northwest Territories'),
  ('CANADA', 'NUNAVUT', 'Nunavut'),
  ('CANADA', 'NU', 'Nunavut'),
  ('CANADA', 'ONTARIO', 'Ontario'),
  ('CANADA', 'ON', 'Ontario'),
  ('CANADA', 'PRINCE EDWARD ISLAND', 'Prince Edward Island'),
  ('CANADA', 'PE', 'Prince Edward Island'),
  ('CANADA', 'QUEBEC', 'Quebec'),
  ('CANADA', 'QC', 'Quebec'),
  ('CANADA', 'QUÉBEC', 'Quebec'),
  ('CANADA', 'SASKATCHEWAN', 'Saskatchewan'),
  ('CANADA', 'SK', 'Saskatchewan'),
  ('CANADA', 'YUKON', 'Yukon'),
  ('CANADA', 'YT', 'Yukon'),
  ('AUSTRALIA', 'AUSTRALIAN CAPITAL TERRITORY', 'Australian Capital Territory'),
  ('AUSTRALIA', 'ACT', 'Australian Capital Territory'),
  ('AUSTRALIA', 'NEW SOUTH WALES', 'New South Wales'),
  ('AUSTRALIA', 'NSW', 'New South Wales'),
  ('AUSTRALIA', 'NORTHERN TERRITORY', 'Northern Territory'),
  ('AUSTRALIA', 'NT', 'Northern Territory'),
  ('AUSTRALIA', 'QUEENSLAND', 'Queensland'),
  ('AUSTRALIA', 'QLD', 'Queensland'),
  ('AUSTRALIA', 'SOUTH AUSTRALIA', 'South Australia'),
  ('AUSTRALIA', 'SA', 'South Australia'),
  ('AUSTRALIA', 'TASMANIA', 'Tasmania'),
  ('AUSTRALIA', 'TAS', 'Tasmania'),
  ('AUSTRALIA', 'VICTORIA', 'Victoria'),
  ('AUSTRALIA', 'VIC', 'Victoria'),
  ('AUSTRALIA', 'WESTERN AUSTRALIA', 'Western Australia'),
  ('AUSTRALIA', 'WA', 'Western Australia'),
  ('AUSTRALIA', 'WEST AUSTRALIA', 'Western Australia'),
  ('UNITED KINGDOM', 'ENGLAND', 'England'),
  ('UNITED KINGDOM', 'SCOTLAND', 'Scotland'),
  ('UNITED KINGDOM', 'SCT', 'Scotland'),
  ('UNITED KINGDOM', 'WALES', 'Wales'),
  ('UNITED KINGDOM', 'NORTHERN IRELAND', 'Northern Ireland');

CREATE FUNCTION public.canonical_region_name(raw_state text, raw_country text DEFAULT NULL)
RETURNS text LANGUAGE sql STABLE SET search_path = public AS $$
  WITH country AS (
    SELECT CASE upper(btrim(raw_country))
      WHEN 'US' THEN 'UNITED STATES' WHEN 'USA' THEN 'UNITED STATES'
      WHEN 'U.S.' THEN 'UNITED STATES' WHEN 'UNITED STATES OF AMERICA' THEN 'UNITED STATES'
      WHEN 'CA' THEN 'CANADA' WHEN 'CAN' THEN 'CANADA'
      WHEN 'AU' THEN 'AUSTRALIA' WHEN 'AUS' THEN 'AUSTRALIA'
      WHEN 'GB' THEN 'UNITED KINGDOM' WHEN 'GBR' THEN 'UNITED KINGDOM'
      WHEN 'UK' THEN 'UNITED KINGDOM'
      ELSE nullif(upper(btrim(raw_country)), '') END AS key
  ), matches AS (
    SELECT min(a.canonical_name) AS name, count(DISTINCT a.canonical_name) AS names
    FROM public.region_name_aliases a CROSS JOIN country c
    WHERE a.alias = upper(btrim(raw_state)) AND (c.key IS NULL OR a.country_key = c.key)
  )
  SELECT CASE WHEN raw_state IS NULL OR upper(btrim(raw_state)) IN ('', 'UNDEFINED', 'UNKNOWN') THEN NULL
    WHEN names = 1 THEN name ELSE btrim(raw_state) END FROM matches;
$$;

CREATE FUNCTION public.normalize_tournament_region()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  NEW.state := public.canonical_region_name(NEW.state, NEW.country);
  RETURN NEW;
END;
$$;
CREATE TRIGGER normalize_tournament_region
BEFORE INSERT OR UPDATE OF state, country ON public.tournaments
FOR EACH ROW EXECUTE FUNCTION public.normalize_tournament_region();

UPDATE public.tournaments SET state = public.canonical_region_name(state, country)
WHERE state IS DISTINCT FROM public.canonical_region_name(state, country);

-- Scryfall-verified printed/flavor names sharing a card identity.
CREATE TABLE public.commander_name_aliases (
  alias text PRIMARY KEY,
  canonical_name text NOT NULL CHECK (alias <> canonical_name),
  oracle_id uuid NOT NULL,
  source_url text NOT NULL
);
ALTER TABLE public.commander_name_aliases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON public.commander_name_aliases FOR SELECT USING (true);
CREATE POLICY "Service role write access" ON public.commander_name_aliases FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.commander_name_aliases TO anon, authenticated;
GRANT ALL ON public.commander_name_aliases TO service_role;
INSERT INTO public.commander_name_aliases VALUES
  ('''Tis But a Scratch!', 'Dismember', 'fd74f8eb-0253-42dd-8277-186d4934da38', 'https://scryfall.com/card/sld/1674/dismember?utm_source=api'),
  ('A Most Helpful Weaver', 'Origin of Spider-Man', '7fbe9056-190f-40a1-bee9-59ebd6f981f5', 'https://scryfall.com/card/om1/14/origin-of-spider-man?utm_source=api'),
  ('A Promise Fulfilled', 'Light Up the Stage', '8d286376-f386-43ab-a9bd-8478fb9e2497', 'https://scryfall.com/card/fca/39/light-up-the-stage?utm_source=api'),
  ('A Trail of Teacups', 'Kraven''s Last Hunt', 'e74efcf2-d77f-4fb5-9027-77e462ec829e', 'https://scryfall.com/card/om1/121/kravens-last-hunt?utm_source=api'),
  ('Aang''s Shelter', 'Teferi''s Protection', '0d4ecdb1-ec90-497f-a7a4-1c68092b8757', 'https://scryfall.com/card/tle/7/teferis-protection?utm_source=api'),
  ('Aang, Ascendant Airbender', 'Serra Ascendant', '27ad3e00-6ffb-48f7-8469-8868d066d1e2', 'https://scryfall.com/card/sld/2291/serra-ascendant?utm_source=api'),
  ('Aang, Awoken Avatar', 'Marit Lage', '48e9147e-59f7-4693-83d7-7f514be871bc', 'https://scryfall.com/card/ttle/1/marit-lage?utm_source=api'),
  ('Abraham Van Helsing', 'Savior of Ollenbock', '1857dc32-8ff1-4519-b1ca-480a5c2d3b3c', 'https://scryfall.com/card/vow/330/savior-of-ollenbock?utm_source=api'),
  ('Absolutely Accurate Actor', 'Phantasmal Image', 'bde94af8-faea-41ff-8eed-ba642eac9968', 'https://scryfall.com/card/sld/2306/phantasmal-image?utm_source=api'),
  ('Absorb into Time', 'Temporal Extortion', '13da5255-2fc5-43a4-a44c-13a5d9ff77c3', 'https://scryfall.com/card/sld/1859/temporal-extortion?utm_source=api'),
  ('Abundant Groot', 'Abundant Growth', '947a2665-2f4d-4193-8768-118f85334549', 'https://scryfall.com/card/sld/870/abundant-growth?utm_source=api'),
  ('Adamantium Bonding Tank', 'The Ozolith', '1946ded1-5f53-409f-b0a6-5433bb0357d2', 'https://scryfall.com/card/sld/1741/the-ozolith?utm_source=api'),
  ('Ademi of the Silkchutes', 'Spectacular Spider-Man', 'eed5e0cc-8f88-4779-bf10-6a823c72df7f', 'https://scryfall.com/card/om1/1/spectacular-spider-man?utm_source=api'),
  ('Aerith''s Curaga Magic', 'Heroic Intervention', '24882fa2-3fe9-4c1b-aa3d-0e6488b9db27', 'https://scryfall.com/card/sld/1872/heroic-intervention?utm_source=api'),
  ('Afternoon Tea 3:00 PM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2549/food?utm_source=api'),
  ('Aggressive Symbiosis', 'Alien Symbiosis', '19504e19-2886-4d28-a813-b798a9a446a2', 'https://scryfall.com/card/om1/49/alien-symbiosis?utm_source=api'),
  ('Aggro Amalgam', 'Voracious Hydra', 'ff8f5a4b-112a-425e-b489-7ee26d1d9fb3', 'https://scryfall.com/card/tmc/54/voracious-hydra?utm_source=api'),
  ('Air Shoes', 'Swiftfoot Boots', 'c8b143ad-43ec-4e0d-a440-e348daa31391', 'https://scryfall.com/card/sld/2096/swiftfoot-boots?utm_source=api'),
  ('Alenni, Brood Recruiter', 'Silk, Web Weaver', '50477dc8-9a2a-41eb-984d-c9e1e78e08a2', 'https://scryfall.com/card/om1/123/silk-web-weaver?utm_source=api'),
  ('Alessos and Pras, Acrobats', 'Spider-Man India', '8933297c-62f1-4df9-91b8-2d3481db77e5', 'https://scryfall.com/card/om1/124/spider-man-india?utm_source=api'),
  ('All-Seeing Toby', 'Sovereign Okinec Ahau', '087b2490-e415-44e2-a674-3b5619a0fad5', 'https://scryfall.com/card/sld/2695/sovereign-okinec-ahau?utm_source=api'),
  ('Altaïr, Brotherhood Mentor', 'Kelsien, the Plague', '5b3326a5-18c5-4d45-90e1-f6d00ca2bced', 'https://scryfall.com/card/sld/1558/kelsien-the-plague?utm_source=api'),
  ('Amunet, Tyrants'' End', 'Queen Marchesa', 'd7ac4be1-dcca-49b6-8ddb-d1b0e6cf2dcf', 'https://scryfall.com/card/sld/1559/queen-marchesa?utm_source=api'),
  ('Ancestral Carvings', 'Pictures of Spider-Man', '4fd74a8c-a4e7-4988-ae02-9a73ab6ec89e', 'https://scryfall.com/card/om1/99/pictures-of-spider-man?utm_source=api'),
  ('Angler''s Shield', 'Biorganic Carapace', '7d27c583-469c-42d7-a547-8c65654e9d95', 'https://scryfall.com/card/om1/125/biorganic-carapace?utm_source=api'),
  ('Anguirus, Armored Killer', 'Gemrazer', '3dfb0c0a-b68f-43b9-8475-28d0192fc4ed', 'https://scryfall.com/card/iko/376/gemrazer?utm_source=api'),
  ('Anima', 'Grief', '0d6b89dc-23fb-48e9-a54b-cea2838ae7c8', 'https://scryfall.com/card/sld/7006/grief?utm_source=api'),
  ('Answer the Call', 'Eladamri''s Call', '4acb6612-54e8-428d-acb6-c7259a5ad6a8', 'https://scryfall.com/card/sld/1770/eladamris-call?utm_source=api'),
  ('Arachnomania', 'Spider-Verse', '7ef7d902-1f05-40b3-8997-dec197b0b678', 'https://scryfall.com/card/om1/75/spider-verse?utm_source=api'),
  ('Arala, Hedron Scaler', 'Beetle, Legacy Criminal', '87972de1-c1d7-408e-8d56-995590f639b8', 'https://scryfall.com/card/om1/25/beetle-legacy-criminal?utm_source=api'),
  ('Archaeon the Everchosen', 'Najeela, the Blade-Blossom', '09619943-6aec-4080-ace5-a0c6ebb23f1c', 'https://scryfall.com/card/sld/1032/najeela-the-blade-blossom?utm_source=api'),
  ('Archangel of Tunes', 'Archangel of Thune', '4f2d4538-dc1d-4c09-964b-b0d7c240fb7d', 'https://scryfall.com/card/sld/2430/archangel-of-thune?utm_source=api'),
  ('Archangler''s Skyrod', 'Web-Shooters', 'ec528198-a38a-4ef7-9804-78a25c94ecc1', 'https://scryfall.com/card/om1/2/web-shooters?utm_source=api'),
  ('Ardyn Izunia', 'Varragoth, Bloodsky Sire', '68b41a04-8cb0-4edf-b488-a219494453ae', 'https://scryfall.com/card/fca/37/varragoth-bloodsky-sire?utm_source=api'),
  ('Argonath, Pillars of the Kings', 'The Ozolith', '1946ded1-5f53-409f-b0a6-5433bb0357d2', 'https://scryfall.com/card/ltc/381z/the-ozolith?utm_source=api'),
  ('Argyr, Tidal Spinner', 'Spider-Byte, Web Warden', '845472ca-3fcb-4bcd-953c-96eb8d914af9', 'https://scryfall.com/card/om1/26/spider-byte-web-warden?utm_source=api'),
  ('Armiger Unleashed', 'Forge Anew', '4df579df-fdbb-418a-af2d-709e140ee569', 'https://scryfall.com/card/sld/7002/forge-anew?utm_source=api'),
  ('Ash, Destined Survivor', 'Puresteel Paladin', '74a62c7b-4753-4af2-b7a1-9a4ae8988801', 'https://scryfall.com/card/sld/1352/puresteel-paladin?utm_source=api'),
  ('Assaultron Invader', 'Walking Ballista', '4b515bb0-f275-4400-8032-3173b799ab40', 'https://scryfall.com/card/pip/880/walking-ballista?utm_source=api'),
  ('Astral Titan', 'Primeval Titan', 'ae83ef2c-960f-4c5b-97cc-52465c687c18', 'https://scryfall.com/card/fca/48/primeval-titan?utm_source=api'),
  ('Atsu, Ghost of Yōtei', 'Tetsuko Umezawa, Fugitive', 'ceeeacbc-01b0-4421-aaca-2ce6cdbe45d7', 'https://scryfall.com/card/sld/7055/tetsuko-umezawa-fugitive?utm_source=api'),
  ('Avatar Sanctuary', 'Cryptolith Rite', '043f869d-b11c-4c0d-9591-2bf0df7bde55', 'https://scryfall.com/card/sld/2293/cryptolith-rite?utm_source=api'),
  ('Avengers Monitoring Station', 'Herald''s Horn', 'c02c5547-b9c9-4b2d-9d12-e87bfba8f2d2', 'https://scryfall.com/card/msc/287/heralds-horn?utm_source=api'),
  ('Awesome Android', 'Containment Construct', '54d48e54-be4a-4a78-a778-b28e74ef7134', 'https://scryfall.com/card/msc/284/containment-construct?utm_source=api'),
  ('Azula, Flame of Ember Island', 'Diaochan, Artful Beauty', 'bf20bc37-3205-45af-a3be-05d6835c0d87', 'https://scryfall.com/card/tle/27/diaochan-artful-beauty?utm_source=api'),
  ('Babygodzilla, Ruin Reborn', 'Pollywog Symbiote', '0a766368-c982-4cba-9638-c7a56978c240', 'https://scryfall.com/card/iko/372/pollywog-symbiote?utm_source=api'),
  ('Backstage Monitor', 'Tigereye Cameo', 'd2be289e-e560-405d-9728-d8a4ee9cbf56', 'https://scryfall.com/card/sld/7093/tigereye-cameo?utm_source=api'),
  ('Bag End', 'Horizon Canopy', '262a5d83-506c-4781-9bc9-1a2b5d83955c', 'https://scryfall.com/card/ltc/396z/horizon-canopy?utm_source=api'),
  ('Balamb Garden', 'Command Beacon', '7e8c2a18-e404-40ff-a9e0-ec3eeb6d576e', 'https://scryfall.com/card/fca/64/command-beacon?utm_source=api'),
  ('Balin''s Tomb', 'Ancient Tomb', '23467047-6dba-4498-b783-1ebc4f74b8c2', 'https://scryfall.com/card/ltc/387z/ancient-tomb?utm_source=api'),
  ('Bane-Marked Leonin', 'Venomized Cat', 'eb54d807-624b-471e-8c44-07322003903e', 'https://scryfall.com/card/om1/50/venomized-cat?utm_source=api'),
  ('Barnabas Tharmr', 'Kraum, Ludevic''s Opus', '5f694f2d-9349-4988-b2b4-788136d4293e', 'https://scryfall.com/card/fca/56/kraum-ludevics-opus?utm_source=api'),
  ('Baron Rivalry', 'Deadly Dispute', '457af74a-02b3-4659-846d-63e482667f34', 'https://scryfall.com/card/fca/33/deadly-dispute?utm_source=api'),
  ('Barrow-Downs', 'Bojuka Bog', '04b7362d-0490-4cb0-b5d7-2a7732f659ce', 'https://scryfall.com/card/ltc/388z/bojuka-bog?utm_source=api'),
  ('Bartz Klauser', 'Winota, Joiner of Forces', '02598a35-1b11-4abe-89cd-fc44c8c36c15', 'https://scryfall.com/card/fca/19/winota-joiner-of-forces?utm_source=api'),
  ('Basil, Cabaretti Loudmouth', 'Flash Thompson, Spider-Fan', 'f536a518-160e-4267-89da-3d34accc6d2c', 'https://scryfall.com/card/om1/3/flash-thompson-spider-fan?utm_source=api'),
  ('Basim, Master Assassin', 'Ramses, Assassin Lord', '170182ed-af1d-442a-8868-d74a96e17f03', 'https://scryfall.com/card/sld/1560/ramses-assassin-lord?utm_source=api'),
  ('Bast''s Blessing', 'Primal Vigor', 'c665544f-557b-4631-a1dc-39571470ca2e', 'https://scryfall.com/card/sld/1749/primal-vigor?utm_source=api'),
  ('Battle Bus', 'Smuggler''s Copter', '49136bdc-bc50-49a2-999a-1ef9c16ea130', 'https://scryfall.com/card/sld/446/smugglers-copter?utm_source=api'),
  ('Battle Cat, Fighting Tiger', 'Fortune, Loyal Steed', 'dc440b62-0bf0-4f23-9210-3550ff0a8d4d', 'https://scryfall.com/card/sld/2790/fortune-loyal-steed?utm_source=api'),
  ('Battle Royale', 'Triumph of the Hordes', '3ded0c0c-40ce-4d14-a9a6-b023bc19ee0e', 'https://scryfall.com/card/sld/445/triumph-of-the-hordes?utm_source=api'),
  ('Battle at the Big Bridge', 'Fatal Push', '16437a83-be52-44cd-a768-a767c9347eb2', 'https://scryfall.com/card/fca/9/fatal-push?utm_source=api'),
  ('Battle of Olympus', 'World at War', '02a8a5cc-62ce-4ae5-aa7d-760124af7d7b', 'https://scryfall.com/card/sld/2208/world-at-war?utm_source=api'),
  ('Battra, Dark Destroyer', 'Dirge Bat', '4746828f-46ea-439f-88de-5e54cc536545', 'https://scryfall.com/card/prm/80935/dirge-bat?utm_source=api'),
  ('Bayo, Irritable Instructor', 'Electro, Assaulting Battery', '3db16fb8-5650-4568-b975-42ad3d44ebcd', 'https://scryfall.com/card/om1/76/electro-assaulting-battery?utm_source=api'),
  ('Beast Man, Savage Henchman', 'Kona, Rescue Beastie', '76372327-41ec-4516-abff-3b612e073629', 'https://scryfall.com/card/sld/2785/kona-rescue-beastie?utm_source=api'),
  ('Beholder''s Charm Ray', 'Bribery', '6d194882-ca37-49bb-ac9f-a751c53850a8', 'https://scryfall.com/card/sld/1786/bribery?utm_source=api'),
  ('Beholder''s Death Ray', 'Snuff Out', '324824cb-f938-401c-b9b5-d8908b431ef0', 'https://scryfall.com/card/sld/1792/snuff-out?utm_source=api'),
  ('Beholder''s Disintegration Ray', 'Fire Covenant', '025939a0-424a-41bf-8fc9-2ef9ea5485f7', 'https://scryfall.com/card/sld/1796/fire-covenant?utm_source=api'),
  ('Beholder''s Enervation Ray', 'Defile', '49dddec0-d958-4810-8c6e-225fc8118c8f', 'https://scryfall.com/card/sld/1793/defile?utm_source=api'),
  ('Beholder''s Fear Ray', 'Drown in the Loch', '0f264e5b-264e-4e97-9a8d-8ae1d6a286ce', 'https://scryfall.com/card/sld/1790/drown-in-the-loch?utm_source=api'),
  ('Beholder''s Paralyzing Ray', 'Oubliette', 'c753e9e3-9374-4e3c-8622-94576a8c1da3', 'https://scryfall.com/card/sld/1794/oubliette?utm_source=api'),
  ('Beholder''s Petrification Ray', 'Blood Money', '75f5d372-4ff9-430c-8302-72472439e0d2', 'https://scryfall.com/card/sld/1789/blood-money?utm_source=api'),
  ('Beholder''s Sleep Ray', 'Stifle', 'b3b00911-ece7-4484-bc36-f211ce72b6cc', 'https://scryfall.com/card/sld/1787/stifle?utm_source=api'),
  ('Beholder''s Slowing Ray', 'Delay', '983caa3f-7089-4e66-825d-4086a5adb9bb', 'https://scryfall.com/card/sld/1788/delay?utm_source=api'),
  ('Beholder''s Telekinetic Ray', 'Fling', '24227761-b50e-4b9e-93a2-e82d053b3e3d', 'https://scryfall.com/card/sld/1795/fling?utm_source=api'),
  ('Belion, the Parched', 'Hydro-Man, Fluid Felon', 'a93a8edf-2879-4cae-b3b9-b46298270823', 'https://scryfall.com/card/om1/27/hydro-man-fluid-felon?utm_source=api'),
  ('Benedikta Harman', 'Ishai, Ojutai Dragonspeaker', '4aae7102-301a-429d-b169-4f462384d55d', 'https://scryfall.com/card/fca/53/ishai-ojutai-dragonspeaker?utm_source=api'),
  ('Benny, Platinum Thief', 'Tinybones, Trinket Thief', '008eda1f-b913-4f04-8c29-5e87c270149e', 'https://scryfall.com/card/sld/2458/tinybones-trinket-thief?utm_source=api'),
  ('Bherna Huntmaster', 'Imperial Recruiter', '4d6a1391-817a-4ddc-840d-886b138eeb3f', 'https://scryfall.com/card/sld/2244/imperial-recruiter?utm_source=api'),
  ('Bhujerba, Floating City', 'City of Brass', 'f25351e3-539b-4bbc-b92d-6480acf4d722', 'https://scryfall.com/card/sch/41/city-of-brass?utm_source=api'),
  ('Big Slime', 'Mitotic Slime', '1162c7ff-c0cb-469a-ad3c-322b0981ae1d', 'https://scryfall.com/card/sld/2815/mitotic-slime?utm_source=api'),
  ('Bio-Quartz Spacegodzilla', 'Brokkos, Apex of Forever', 'e9137b54-3464-4f57-95e3-f94bf2ac854e', 'https://scryfall.com/card/iko/378/brokkos-apex-of-forever?utm_source=api'),
  ('Biollante, Plant Beast Form', 'Nethroi, Apex of Death', '66bef5a7-79b7-4a9c-98dc-8670f867f04c', 'https://scryfall.com/card/iko/380/nethroi-apex-of-death?utm_source=api'),
  ('Black Panther''s Claws', 'Hammer of Nazahn', 'e3955573-3db5-490e-903e-65e0172a9202', 'https://scryfall.com/card/msc/427/hammer-of-nazahn?utm_source=api'),
  ('Black Panther''s Redirection', 'Narset''s Reversal', 'd55f6c70-321f-4fb4-bd33-0850ae1a7c36', 'https://scryfall.com/card/mar/58/narsets-reversal?utm_source=api'),
  ('Blanka, Ferocious Friend', 'The Howling Abomination', '4a67946e-8903-4994-9641-d31fbb62082c', 'https://scryfall.com/card/sld/431/the-howling-abomination?utm_source=api'),
  ('Blessing of the Oracle', 'Akroma''s Will', 'fd949f82-fc10-4e37-8aa9-6c7569fe3c55', 'https://scryfall.com/card/fca/21/akromas-will?utm_source=api'),
  ('Bloodbender''s Rise', 'Bloodchief Ascension', 'd5ea905b-4bb6-48d0-9082-c472703db550', 'https://scryfall.com/card/tle/23/bloodchief-ascension?utm_source=api'),
  ('Bone Throne', 'Throne of the God-Pharaoh', 'ea750169-1f6f-40c2-96e9-55719e103a63', 'https://scryfall.com/card/sld/2792/throne-of-the-god-pharaoh?utm_source=api'),
  ('Boogie Bomb', 'Pyrite Spellbomb', '2c10cae2-951a-4f4f-94e4-8713b58d07dd', 'https://scryfall.com/card/sld/676/pyrite-spellbomb?utm_source=api'),
  ('Borys, the Spider Rider', 'Scarlet Spider, Ben Reilly', '13ab2f3f-f65e-42b5-b743-39b30a4c4751', 'https://scryfall.com/card/om1/126/scarlet-spider-ben-reilly?utm_source=api'),
  ('Both Down', 'Bone Splinters', '0c936582-d4c0-4da8-bc7e-49da5a433939', 'https://scryfall.com/card/sld/1037/bone-splinters?utm_source=api'),
  ('Bow, Master Archer', 'Hajar, Loyal Bodyguard', '63584001-7f58-42ee-b072-914baa66c78a', 'https://scryfall.com/card/sld/2781/hajar-loyal-bodyguard?utm_source=api'),
  ('Brachiosaurus', 'Colossal Dreadmaw', '08c7db90-c0cf-4482-b7ee-bb033e5996d2', 'https://scryfall.com/card/sld/740%E2%98%85/colossal-dreadmaw?utm_source=api'),
  ('Brachydios, Brutish Indigo', 'Kalamax, the Stormsire', 'b8501a37-23e4-4873-80cb-d1c0f6c95155', 'https://scryfall.com/card/sld/2252/kalamax-the-stormsire?utm_source=api'),
  ('Brako, Heartless Hunter', 'Kraven the Hunter', '3e2bfa3a-ae83-453a-8e3f-ca6205a9af12', 'https://scryfall.com/card/om1/127/kraven-the-hunter?utm_source=api'),
  ('Breakfast 7:00 AM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2545/food?utm_source=api'),
  ('Bridge of Khazad-dûm', 'Ensnaring Bridge', 'dade5835-ccaf-45e3-b9a3-46017e0384b3', 'https://scryfall.com/card/ltc/380z/ensnaring-bridge?utm_source=api'),
  ('Bring Out Your Dead!', 'Buried Alive', '8203c621-a1a0-4865-8c9a-0d4064c86107', 'https://scryfall.com/card/sld/1673/buried-alive?utm_source=api'),
  ('Bucklebury Ferry', 'Oboro, Palace in the Clouds', '645fb11b-d684-4bec-8532-8fa97e8f7b28', 'https://scryfall.com/card/ltc/401z/oboro-palace-in-the-clouds?utm_source=api'),
  ('Buttercup, Provincial Princess', 'Sisay, Weatherlight Captain', 'fb777610-7562-4d9d-8497-62c562e6d7cb', 'https://scryfall.com/card/sld/1444/sisay-weatherlight-captain?utm_source=api'),
  ('Cabin of the Dead', 'Field of the Dead', 'aa959340-c869-4caa-92c7-572bd8d23eef', 'https://scryfall.com/card/sld/1356/field-of-the-dead?utm_source=api'),
  ('Cactarantula Saddle', 'Spider-Suit', 'ba08b4cf-9a13-40fd-8522-9504d2ff1a19', 'https://scryfall.com/card/om1/161/spider-suit?utm_source=api'),
  ('Caldaia Brawlers', 'Inner Demons Gangsters', '40b43763-3fbf-4ecd-8187-5d2c2c9cda82', 'https://scryfall.com/card/om1/51/inner-demons-gangsters?utm_source=api'),
  ('Calliope''s Song', 'Seething Song', '64bf8929-f5f2-4d50-8667-13b1d007bcfc', 'https://scryfall.com/card/sld/7051/seething-song?utm_source=api'),
  ('Cam and Farrik, Havoc Duo', 'Hobgoblin, Mantled Marauder', '1d453331-6b8e-4d3d-b658-683eab2760da', 'https://scryfall.com/card/om1/77/hobgoblin-mantled-marauder?utm_source=api'),
  ('Captain America''s Aid', 'Sigarda''s Aid', '4f5f2792-0cc4-4caa-b798-2ee9597f2524', 'https://scryfall.com/card/sld/1727/sigardas-aid?utm_source=api'),
  ('Caras Galadhon', 'Tranquil Thicket', '9f8fe514-77ed-41b4-a6f3-c6f095bb97be', 'https://scryfall.com/card/pf23/2/tranquil-thicket?utm_source=api'),
  ('Carlo, Suave Schemer', 'Prowler, Clawed Thief', '76742bfc-ae99-4b06-b29d-e0e41d92ae14', 'https://scryfall.com/card/om1/128/prowler-clawed-thief?utm_source=api'),
  ('Carriage of Dreams', 'Passenger Ferry', 'e9832d58-0ee6-4641-a9fd-d34d54b3b11c', 'https://scryfall.com/card/om1/162/passenger-ferry?utm_source=api'),
  ('Cascade of Song', 'Halo Fountain', '36a9de4c-8073-475d-8679-e50844eef09e', 'https://scryfall.com/card/sld/2431/halo-fountain?utm_source=api'),
  ('Cast-Off Consort', 'Bloodletter of Aclazotz', '469956a2-7cd4-4695-b8f4-c841526f160d', 'https://scryfall.com/card/sld/2502/bloodletter-of-aclazotz?utm_source=api'),
  ('Castle Dracula', 'Voldaren Estate', 'fb0c0426-f1a6-4e52-9242-627786d3119a', 'https://scryfall.com/card/vow/403/voldaren-estate?utm_source=api'),
  ('Castle Ravenloft', 'Voldaren Estate', 'fb0c0426-f1a6-4e52-9242-627786d3119a', 'https://scryfall.com/card/sld/2504/voldaren-estate?utm_source=api'),
  ('Castle Shimura', 'Eiganjo Castle', '895a0e00-20a9-44f8-9215-66edcdf016b7', 'https://scryfall.com/card/sld/2230/eiganjo-castle?utm_source=api'),
  ('Castle of Aaargh', 'Dark Depths', 'c9b82110-7dfd-4617-9399-9510be449043', 'https://scryfall.com/card/sld/1680/dark-depths?utm_source=api'),
  ('Catra, Force Captain', 'Kutzil, Malamet Exemplar', '3233af43-7826-4895-b67e-03c6102c2cd5', 'https://scryfall.com/card/sld/2782/kutzil-malamet-exemplar?utm_source=api'),
  ('Cecil Harvey', 'Tymna the Weaver', 'd15642e4-e61c-4d29-af48-de837991245e', 'https://scryfall.com/card/fca/18/tymna-the-weaver?utm_source=api'),
  ('Centurion of the Marked', 'Lord of the Undead', '7714af0e-41d9-4609-967f-27233b46055f', 'https://scryfall.com/card/pip/873/lord-of-the-undead?utm_source=api'),
  ('Champion of Kotoko', 'Champion of Lambholt', 'c549b0fd-1e08-4873-952e-a14dc45a0fd2', 'https://scryfall.com/card/sld/2245/champion-of-lambholt?utm_source=api'),
  ('Chancla relámpago', 'Lightning Greaves', 'ca204b66-8d0c-431a-8d34-282f7c2d17da', 'https://scryfall.com/card/sld/2062/lightning-greaves?utm_source=api'),
  ('Chaos Emerald', 'Lotus Petal', '32e5339e-9e4f-46f8-b305-f9d6d3ba8bb5', 'https://scryfall.com/card/sld/7037/lotus-petal?utm_source=api'),
  ('Chaos Theory', 'Chaos Warp', '07a0cba9-8768-4fd9-a3d5-b0f83b4bf8e8', 'https://scryfall.com/card/sld/741%E2%98%85/chaos-warp?utm_source=api'),
  ('Chaotic Chaotician', 'Laboratory Maniac', 'aa286dd5-aa19-446d-9003-684d81eb57ca', 'https://scryfall.com/card/sld/1394%E2%98%85/laboratory-maniac?utm_source=api'),
  ('Chief Jim Hopper', 'Sophina, Spearsage Deserter', '095dabda-4570-4764-8d62-4a29eb19d3e6', 'https://scryfall.com/card/sld/341/sophina-spearsage-deserter?utm_source=api'),
  ('Chizak, Apex Arachnosaur', 'Spider-Rex, Daring Dino', '58b771d4-dfaf-4189-a5f6-4bc0fb4c0fa3', 'https://scryfall.com/card/om1/100/spider-rex-daring-dino?utm_source=api'),
  ('Chosen by Valgavoth', 'With Great Power . . .', 'dfedb968-f27c-4117-aff6-da707dd43e82', 'https://scryfall.com/card/om1/4/with-great-power-?utm_source=api'),
  ('Chun-Li, Countless Kicks', 'Zethi, Arcane Blademaster', 'ac136d46-32b7-4222-a840-b8be011c1872', 'https://scryfall.com/card/sld/432/zethi-arcane-blademaster?utm_source=api'),
  ('Cirina Bargainspinner', 'Sun-Spider, Nimble Webber', '2d961997-4f5f-4ce2-b062-11411147e2f7', 'https://scryfall.com/card/om1/130/sun-spider-nimble-webber?utm_source=api'),
  ('Clandestine Work', 'Risky Research', '47d52cd7-d72f-455f-aad3-70f08d54691f', 'https://scryfall.com/card/om1/52/risky-research?utm_source=api'),
  ('Clive Rosfield', 'Vial Smasher the Fierce', '1b355139-4891-436c-9079-0ce17ecc2d65', 'https://scryfall.com/card/fca/59/vial-smasher-the-fierce?utm_source=api'),
  ('Clive''s Invictus Blade', 'Blade of Selves', '9c329f3d-4d0a-4012-8aa6-92afdd120a52', 'https://scryfall.com/card/sld/1864/blade-of-selves?utm_source=api'),
  ('Cloud Strife', 'Najeela, the Blade-Blossom', '09619943-6aec-4080-ace5-a0c6ebb23f1c', 'https://scryfall.com/card/fca/42/najeela-the-blade-blossom?utm_source=api'),
  ('Cloud''s Buster Sword', 'Umezawa''s Jitte', '1da10d5c-36a8-473f-a5d4-782ad61d8057', 'https://scryfall.com/card/sld/1865/umezawas-jitte?utm_source=api'),
  ('Colonel John Jameson', 'Huntmaster of the Fells', '582328cd-660d-47a4-bb23-e91e80b9a907', 'https://scryfall.com/card/lmar/3/huntmaster-of-the-fells-ravager-of-the-fells?utm_source=api'),
  ('Community Center', 'Fountainport', '94e8b0a9-44a1-4dce-8d44-78681ae638a1', 'https://scryfall.com/card/sld/2810/fountainport?utm_source=api'),
  ('Confessor''s Bindings', 'Rent Is Due', '3fe1530d-bcf2-440b-a905-5a2216daa7eb', 'https://scryfall.com/card/om1/6/rent-is-due?utm_source=api'),
  ('Cordyceps Excision', 'Cabal Ritual', '5b5bf1fa-6502-4790-b66b-f0f8504ebc7c', 'https://scryfall.com/card/sld/2199/cabal-ritual?utm_source=api'),
  ('Cordyceps Rat King', 'Mycoloth', 'd7fd16ce-282d-49cd-b2b4-0d25935e7a72', 'https://scryfall.com/card/sld/2205/mycoloth?utm_source=api'),
  ('Count Dracula', 'Sorin the Mirthless', 'fbffaf9f-40e7-4113-a037-533b733cebce', 'https://scryfall.com/card/vow/337/sorin-the-mirthless?utm_source=api'),
  ('Cow-tapult', 'Goblin Bombardment', 'edad60c6-80de-4033-af1b-a703ac332983', 'https://scryfall.com/card/sld/825/goblin-bombardment?utm_source=api'),
  ('Cozy Headphones', 'Paradise Mantle', 'c1121b83-1ba2-473d-89c9-e3bbd4529072', 'https://scryfall.com/card/sld/2825/paradise-mantle?utm_source=api'),
  ('Crack the Vault', 'Grim Tutor', 'e62f8d69-a559-4f13-a5c9-5fb750b4af2c', 'https://scryfall.com/card/sld/444/grim-tutor?utm_source=api'),
  ('Crash, Reckless Endrider', 'Shriek, Treblemaker', '5773ae05-44bc-423c-846c-f323dd8a5079', 'https://scryfall.com/card/om1/131/shriek-treblemaker?utm_source=api'),
  ('Cren, Undercity Dreamer', 'Miles Morales', 'be48c721-bdc6-4f2c-96d6-82d934b31615', 'https://scryfall.com/card/om1/102/miles-morales-ultimate-spider-man?utm_source=api'),
  ('Crime-Scene Instructor', 'Selfless Police Captain', 'ece77a64-8d99-430e-8407-bdb321828d63', 'https://scryfall.com/card/om1/8/selfless-police-captain?utm_source=api'),
  ('Crimson Moonlight', 'Blind Obedience', '5d998c09-7d89-4265-ada4-6d80cbf56dae', 'https://scryfall.com/card/sld/2246/blind-obedience?utm_source=api'),
  ('Croft Manor', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/792/command-tower?utm_source=api'),
  ('Cruel Caracals', 'Kraven''s Cats', '976db753-9887-448a-8e67-ec7937b6505c', 'https://scryfall.com/card/om1/103/kravens-cats?utm_source=api'),
  ('Crystal of Altar Cave', 'Chromatic Lantern', '539f5396-d99a-417d-a84c-dff7930b5900', 'https://scryfall.com/card/fca/61/chromatic-lantern?utm_source=api'),
  ('Custom Caravan Deck', 'The Deck of Many Things', '91df4cf5-d7ec-4fcd-87ed-e075ef6ceba9', 'https://scryfall.com/card/sld/2460/the-deck-of-many-things?utm_source=api'),
  ('Cybertron', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/710/command-tower?utm_source=api'),
  ('Da Vulcha', 'Skysovereign, Consul Flagship', '50b14338-9318-4327-a1dd-c0ef38903cc4', 'https://scryfall.com/card/sld/1029/skysovereign-consul-flagship?utm_source=api'),
  ('Damning Caress', 'Venom''s Hunger', '8388faa0-f64e-4b01-836e-617f99b808a4', 'https://scryfall.com/card/om1/54/venoms-hunger?utm_source=api'),
  ('Dance Battle', 'Dance of Many', '72e1a239-11a7-4dbe-b093-65d395e3ccc9', 'https://scryfall.com/card/sld/442/dance-of-many?utm_source=api'),
  ('Darkness of Eternity', 'Dark Ritual', '53f7c868-b03e-4fc2-8dcf-a75bbfa3272b', 'https://scryfall.com/card/fca/8/dark-ritual?utm_source=api'),
  ('Darval, Whose Web Protects', 'Spider-Man, Web-Slinger', '505231d8-714f-4c5b-a635-d1662bd18a78', 'https://scryfall.com/card/om1/9/spider-man-web-slinger?utm_source=api'),
  ('Daryl, Hunter of Walkers', 'Hansk, Slayer Zealot', 'd818f863-17ee-4387-94bf-d7e6e8ab590c', 'https://scryfall.com/card/sld/144/hansk-slayer-zealot?utm_source=api'),
  ('Data Scrubber', 'Mechanical Mobster', 'b0672aa3-3207-4ff8-af8f-bdabacbb4d04', 'https://scryfall.com/card/om1/163/mechanical-mobster?utm_source=api'),
  ('Dawn Warriors'' Legacy', 'Mizzix''s Mastery', '40362fe0-a1a9-4d76-8c35-eac474b91af5', 'https://scryfall.com/card/fca/41/mizzixs-mastery?utm_source=api'),
  ('Deathflame Burst', 'Electro''s Bolt', 'e9222f89-e495-4502-bb0c-f5e802686b01', 'https://scryfall.com/card/om1/78/electros-bolt?utm_source=api'),
  ('Demera, Soul of a Spider', 'Mary Jane Watson', '6d44c87b-8945-4c39-b034-7690cf483992', 'https://scryfall.com/card/om1/132/mary-jane-watson?utm_source=api'),
  ('Denting Blows', 'Krosan Grip', '3e39224c-72ce-4ecc-aa17-12c071ea1f3e', 'https://scryfall.com/card/sld/481/krosan-grip?utm_source=api'),
  ('Desecrex, Gift of Servitude', 'Carnage, Crimson Chaos', 'c0efafc6-8ffb-4908-ae64-3f391722370a', 'https://scryfall.com/card/om1/133/carnage-crimson-chaos?utm_source=api'),
  ('Destoroyah, Perfect Lifeform', 'Everquill Phoenix', '56ba78c1-d1eb-4cc1-b70d-98c35d2972ba', 'https://scryfall.com/card/iko/374/everquill-phoenix?utm_source=api'),
  ('Destroy the Dead', 'Vanquish the Horde', 'a332e80a-dc51-4dc6-bc85-e114a1c6fdb8', 'https://scryfall.com/card/sld/1353/vanquish-the-horde?utm_source=api'),
  ('Detect Intrusion', 'Spider-Sense', 'c4485bf9-e7ff-48b5-a983-02900939ee9d', 'https://scryfall.com/card/om1/28/spider-sense?utm_source=api'),
  ('Dhalsim, Pliable Pacifist', 'Tadeas, Juniper Ascendant', 'b4b5b928-8b98-4f65-9f15-212859874fe4', 'https://scryfall.com/card/sld/433/tadeas-juniper-ascendant?utm_source=api'),
  ('Diabolos, Guardian Force', 'Death''s Shadow', 'e08722b3-0f79-4c82-b298-603e04a37857', 'https://scryfall.com/card/sch/40/deaths-shadow?utm_source=api'),
  ('Diligent Webkeepers', 'Web-Warriors', '3b23e4f8-882d-4cce-9b61-171ae2cc3a18', 'https://scryfall.com/card/om1/134/web-warriors?utm_source=api'),
  ('Dinner 6:00 PM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2550/food?utm_source=api'),
  ('Doc Ock, Armed and Dangerous', 'Lorthos, the Tidemaker', 'd9fd4ff3-5ada-40f4-b949-6fe65624a0c4', 'https://scryfall.com/card/mar/10/lorthos-the-tidemaker?utm_source=api'),
  ('Dogmeat, Constant Companion', 'Yoshimaru, Ever Faithful', '963834c8-42df-4ee6-9b45-b9de88ce2eac', 'https://scryfall.com/card/sld/2463/yoshimaru-ever-faithful?utm_source=api'),
  ('Dol Amroth', 'Minamo, School at Water''s Edge', '17784f90-89a1-47a5-83ef-ae60dfc30bd1', 'https://scryfall.com/card/ltc/399z/minamo-school-at-waters-edge?utm_source=api'),
  ('Donnie''s Bō', 'Shadowspear', '8b27326f-e7b8-4a4d-b589-df459246d19a', 'https://scryfall.com/card/pza/17/shadowspear?utm_source=api'),
  ('Doom Variant', 'Roaming Throne', '3640c29b-1534-4952-b297-619ade948431', 'https://scryfall.com/card/mar/99/roaming-throne?utm_source=api'),
  ('Dorat, the Perfect Pet', 'Sprite Dragon', 'a9d8ab76-70a4-475e-b87e-4737c090553a', 'https://scryfall.com/card/iko/382/sprite-dragon?utm_source=api'),
  ('Doric, Nature''s Warden', 'Casal, Lurkwood Pathfinder', 'b7bdb688-f8ee-4d22-a679-37a2ecd390a1', 'https://scryfall.com/card/sld/1241/casal-lurkwood-pathfinder-casal-pathbreaker-owlbear?utm_source=api'),
  ('Dr. Ian Malcolm', 'Atla Palani, Nest Tender', 'b56cebe0-3752-4ce5-afbd-911543784015', 'https://scryfall.com/card/sld/1397%E2%98%85/atla-palani-nest-tender?utm_source=api'),
  ('Dr. John Seward', 'Torens, Fist of the Angels', '2cb96408-9195-4e41-ad9a-f8c74fbad083', 'https://scryfall.com/card/vow/344/torens-fist-of-the-angels?utm_source=api'),
  ('Dracula the Voyager', 'Edgar, Charmed Groom', '96cb97ca-4ce0-4d33-86fb-4db4ce1956be', 'https://scryfall.com/card/vow/341/edgar-charmed-groom-edgar-markovs-coffin?utm_source=api'),
  ('Dracula''s Tomb', 'Phyrexian Tower', '1861e642-21d5-4232-89f3-b5557f2946c1', 'https://scryfall.com/card/sld/208/phyrexian-tower?utm_source=api'),
  ('Dracula, Blood Immortal', 'Falkenrath Forebear', '940080ce-c504-48c8-a763-326fef907217', 'https://scryfall.com/card/vow/334/falkenrath-forebear?utm_source=api'),
  ('Dracula, Lord of Blood', 'Voldaren Bloodcaster', 'a720f3d3-c2d7-4e50-8cc6-600120380e9c', 'https://scryfall.com/card/vow/338/voldaren-bloodcaster-bloodbat-summoner?utm_source=api'),
  ('Dragon of Mount Gulg', 'Ancient Copper Dragon', '48daee9d-ddaf-410f-8c3a-12fa1064ab56', 'https://scryfall.com/card/fca/12/ancient-copper-dragon?utm_source=api'),
  ('Dreadfang, Loathed by Fans', 'Kraven, Proud Predator', '12b8b4bf-ba85-419c-8005-1ec34b2b1deb', 'https://scryfall.com/card/om1/135/kraven-proud-predator?utm_source=api'),
  ('Drix Interception', 'Amazing Acrobatics', '0466f23c-d07c-4015-82d5-eab4b226f1ff', 'https://scryfall.com/card/om1/29/amazing-acrobatics?utm_source=api'),
  ('Druneth, Reviver of the Hive', 'Jackal, Genius Geneticist', '5998f07e-01f9-4d02-94dd-867c7166463f', 'https://scryfall.com/card/om1/136/jackal-genius-geneticist?utm_source=api'),
  ('Dual-Bladed Hunter', 'Grand Abolisher', 'c749f23c-40c0-4159-b84c-a70cbb062c14', 'https://scryfall.com/card/sld/2241/grand-abolisher?utm_source=api'),
  ('Duskmourn''s Claim', 'Parker Luck', '03d1a4e9-3ebc-491f-8741-5d933b500abf', 'https://scryfall.com/card/om1/55/parker-luck?utm_source=api'),
  ('Dustin, Gadget Genius', 'Hargilde, Kindly Runechanter', '747009e7-da07-48c7-b838-687f19b884ea', 'https://scryfall.com/card/sld/342/hargilde-kindly-runechanter?utm_source=api'),
  ('Dwight Schrute, Hay King', 'Heliod, Sun-Crowned', '63e596a2-9126-4af6-8782-c38687d664ad', 'https://scryfall.com/card/sld/2165/heliod-sun-crowned?utm_source=api'),
  ('Dwight o'' Lantern', 'Reaper King', '70034860-5198-421f-871d-7c1676337b6e', 'https://scryfall.com/card/sld/2170/reaper-king?utm_source=api'),
  ('Dwight''s Weapon Stash', 'Steelshaper''s Gift', 'd9abda7e-6ca2-42ea-ab24-c542e57014f1', 'https://scryfall.com/card/sld/2166/steelshapers-gift?utm_source=api'),
  ('Dwight, Assistant (to the) King', 'Baral, Chief of Compliance', 'baf80db7-2ca8-4bfc-b5b6-25ed51878dd7', 'https://scryfall.com/card/sld/2168/baral-chief-of-compliance?utm_source=api'),
  ('E. Honda, Sumo Champion', 'Baldin, Century Herdmaster', '14493624-fdc7-4630-9b1e-f35668651108', 'https://scryfall.com/card/sld/428/baldin-century-herdmaster?utm_source=api'),
  ('Earth Rumble Triumph', 'Return of the Wildspeaker', '2b76f9e9-cd28-4eaf-8674-215c34263f96', 'https://scryfall.com/card/tle/44/return-of-the-wildspeaker?utm_source=api'),
  ('Earth''s Mightiest Emblem', 'Arcane Signet', '0bc7f093-bef0-4f1a-852c-4b75ebf54838', 'https://scryfall.com/card/sld/908/arcane-signet?utm_source=api'),
  ('Eccentric Arachnologist', 'Guy in the Chair', '83eb74df-1c77-48b0-83be-55d7aa4d3618', 'https://scryfall.com/card/om1/104/guy-in-the-chair?utm_source=api'),
  ('Ecto-1', 'Unlicensed Hearse', 'c640654c-487e-4a2c-aced-126ed835b78f', 'https://scryfall.com/card/sld/1772/unlicensed-hearse?utm_source=api'),
  ('Eddie the Judge', 'Bruvac the Grandiloquent', '274b999f-f193-48fd-9a4a-0fdaf535e6c3', 'https://scryfall.com/card/sld/2181/bruvac-the-grandiloquent?utm_source=api'),
  ('Eddie, Ghost of the Navigator', 'Captain N''ghathrod', 'cfb23c6b-6e4a-4fc9-b3bb-a3ddc2ba06b8', 'https://scryfall.com/card/sld/2183/captain-nghathrod?utm_source=api'),
  ('Eddie, Lord of Light', 'Nekusar, the Mindrazer', '8a5e3c8e-8e22-49b9-8ee5-4a36361f0da6', 'https://scryfall.com/card/sld/2184/nekusar-the-mindrazer?utm_source=api'),
  ('Edea Kramer', 'Teferi, Mage of Zhalfir', '2b6cbd55-5adc-4a34-ac45-8531705a7ee1', 'https://scryfall.com/card/fca/32/teferi-mage-of-zhalfir?utm_source=api'),
  ('Edgin, Larcenous Lutenist', 'Bohn, Beguiling Balladeer', 'ab31b652-ddf2-480f-a955-e8b5c87728f9', 'https://scryfall.com/card/sld/1242/bohn-beguiling-balladeer?utm_source=api'),
  ('Edoras, Capital of Rohan', 'Hammerheim', 'c7476beb-7923-4994-8476-bc69187ecb72', 'https://scryfall.com/card/ltc/518/hammerheim?utm_source=api'),
  ('Edward, Jackdaw Captain', 'Admiral Beckett Brass', '43b5e462-d860-473d-828f-6c513fc7768a', 'https://scryfall.com/card/sld/1561/admiral-beckett-brass?utm_source=api'),
  ('Egg Hammer', 'Myr Battlesphere', 'c53ba31a-ba27-4e17-9a92-311acb1cab29', 'https://scryfall.com/card/sld/2097/myr-battlesphere?utm_source=api'),
  ('Egg Pawn', 'Myr', 'bf690282-125f-431c-a363-39f6772324c8', 'https://scryfall.com/card/sld/2101/myr?utm_source=api'),
  ('Egrix the Bile Bulwark', 'Gwenom, Remorseless', 'c48cf135-b280-4e9f-a9d9-225104870741', 'https://scryfall.com/card/om1/56/gwenom-remorseless?utm_source=api'),
  ('Eivor, Raven Clan Champion', 'Najeela, the Blade-Blossom', '09619943-6aec-4080-ace5-a0c6ebb23f1c', 'https://scryfall.com/card/sld/1557/najeela-the-blade-blossom?utm_source=api'),
  ('El Dorado Sarcophagus', 'Whip of Erebos', '53987a39-c18c-4c13-b1ea-fd1b2a369f9e', 'https://scryfall.com/card/sld/2218/whip-of-erebos?utm_source=api'),
  ('Elektra, Deadly Assassin', 'Massacre Girl', '63e6cb7d-cc27-4200-85fc-ff6472318c1a', 'https://scryfall.com/card/mar/67/massacre-girl?utm_source=api'),
  ('Elessar, the Elfstone', 'Cloudstone Curio', '5cd2fd32-4da2-40eb-b003-c0b9a9ec91c1', 'https://scryfall.com/card/ltc/379z/cloudstone-curio?utm_source=api'),
  ('Eleven, the Mage', 'Cecily, Haunted Mage', 'a726c27d-2955-4d41-b8a6-fca654c020a2', 'https://scryfall.com/card/sld/343/cecily-haunted-mage?utm_source=api'),
  ('Elevenses 11:00 AM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2547/food?utm_source=api'),
  ('Ellie''s Rage', 'Dictate of Erebos', '7c777a41-e40a-4b40-96bf-8ddd5c12924c', 'https://scryfall.com/card/sld/2204/dictate-of-erebos?utm_source=api'),
  ('Emet-Selch, Ascian', 'K''rrik, Son of Yawgmoth', 'cbe3a4e7-5dbe-4f58-8ee6-a1762b65acfd', 'https://scryfall.com/card/fca/36/krrik-son-of-yawgmoth?utm_source=api'),
  ('Encore Electromancer', 'Snapcaster Mage', '2bb2eda7-3b38-4c56-870f-c3218a1056f5', 'https://scryfall.com/card/sld/808/snapcaster-mage?utm_source=api'),
  ('Endwalker', 'Brainstorm', '36cd2364-d113-47d1-b2c4-b088d9eb88dd', 'https://scryfall.com/card/fca/28/brainstorm?utm_source=api'),
  ('Erebor Heirloom', 'Fellwar Stone', '95560508-7ac9-4be9-8a3f-3c7d5b52807b', 'https://scryfall.com/card/sld/2557/fellwar-stone?utm_source=api'),
  ('Error-9, Viral Node', 'Living Brain, Mechanical Marvel', 'b255e13d-01b2-4348-80bd-8d9a8f29be91', 'https://scryfall.com/card/om1/165/living-brain-mechanical-marvel?utm_source=api'),
  ('Escape Containment', 'Incarnation Technique', '0ab9539d-3461-4936-95cd-4c229308c4a4', 'https://scryfall.com/card/sld/1776/incarnation-technique?utm_source=api'),
  ('Evil Warriors'' Shroud', 'Necrogen Mists', 'db25d48e-e5eb-4364-9d7a-f9757ee4ccbe', 'https://scryfall.com/card/sld/2776/necrogen-mists?utm_source=api'),
  ('Evil-Lyn, Evil Warrior Goddess', 'Ertai Resurrected', '3d038f7c-95fa-4b71-8f74-b9b4dd45cde0', 'https://scryfall.com/card/sld/2786/ertai-resurrected?utm_source=api'),
  ('Exclusive Nightclub', 'Oscorp Industries', 'f432eb6a-f1bf-4ce7-b915-1488dccb4bb9', 'https://scryfall.com/card/om1/179/oscorp-industries?utm_source=api'),
  ('Eztli of the Thousand Moons', 'Starling, Aerial Ally', '13fd7ca6-c278-409f-a9c4-57f16051ffce', 'https://scryfall.com/card/om1/10/starling-aerial-ally?utm_source=api'),
  ('FAS-BOR7 Horus', 'Blightsteel Colossus', 'e80772e2-8623-4094-81a2-70828b2b151c', 'https://scryfall.com/card/sld/2223/blightsteel-colossus?utm_source=api'),
  ('Fal''Cie Paradise', 'Carpet of Flowers', '2ffc6372-f63b-4f32-8dd0-2d7938aeb412', 'https://scryfall.com/card/fca/44/carpet-of-flowers?utm_source=api'),
  ('Fangorn Forest', 'Yavimaya, Cradle of Growth', '8dd5f5af-d2d8-4356-8617-8381081b930c', 'https://scryfall.com/card/ltc/407z/yavimaya-cradle-of-growth?utm_source=api'),
  ('Fatalis, the Black Dragon', 'Ziatora, the Incinerator', 'd46c3fb6-f1c7-4a96-ae42-5bce17fc7c1d', 'https://scryfall.com/card/sld/2238/ziatora-the-incinerator?utm_source=api'),
  ('Fateweaver', 'Radioactive Spider', 'f15bd5c0-99ff-42c6-8eed-48de6df81b61', 'https://scryfall.com/card/om1/105/radioactive-spider?utm_source=api'),
  ('Favored Fighter', 'Professional Wrestler', '3dd92eea-02ca-4e55-8f69-8c8059dd7ee6', 'https://scryfall.com/card/om1/106/professional-wrestler?utm_source=api'),
  ('Fearsome Ridgeline', 'Daily Bugle Building', '483e0c6c-8131-486c-b482-cc3396c9786b', 'https://scryfall.com/card/om1/180/daily-bugle-building?utm_source=api'),
  ('Feral Felix', 'Barrowgoyf', '74c0164c-130f-4572-9066-626c77f6e2ff', 'https://scryfall.com/card/sld/2702/barrowgoyf?utm_source=api'),
  ('Fezzik, Rhyming Giant', 'Brion Stoutarm', 'b816b3cc-ae4b-4fb7-8b1a-e01ab83459a3', 'https://scryfall.com/card/sld/1450/brion-stoutarm?utm_source=api'),
  ('Fire Nation Tank Train', 'Noxious Gearhulk', 'a77b5be2-f361-4135-ba25-670a74d268ac', 'https://scryfall.com/card/tle/25/noxious-gearhulk?utm_source=api'),
  ('Fire-Brained Scheme', 'Heroes'' Hangout', '43306a78-85b5-4df4-a018-75dd75aa8997', 'https://scryfall.com/card/om1/79/heroes-hangout?utm_source=api'),
  ('Firion, Swordmaster', 'Sram, Senior Edificer', '7e00b0cd-d212-4604-ba07-da21f4fe00b0', 'https://scryfall.com/card/fca/3/sram-senior-edificer?utm_source=api'),
  ('Fizik, Etherium Mechanic', 'Iron Spider, Stark Upgrade', 'e123fd7d-ace9-48a4-9510-eedcc837d8e8', 'https://scryfall.com/card/om1/166/iron-spider-stark-upgrade?utm_source=api'),
  ('Fog Crawler', 'Vigor', '70787d8b-0a40-43ea-837a-9617dc13e7e5', 'https://scryfall.com/card/pip/875/vigor?utm_source=api'),
  ('Forge, Neverwinter Charlatan', 'Evin, Waterdeep Opportunist', 'f688f839-c7c2-45a9-8c60-9fdb030803e6', 'https://scryfall.com/card/sld/1239/evin-waterdeep-opportunist?utm_source=api'),
  ('Franklin''s Finality', 'Annie Joins Up', '4c3ad545-b375-44a7-a24e-58baacc4e4b6', 'https://scryfall.com/card/msc/403/annie-joins-up?utm_source=api'),
  ('Freestrider Aces', 'Wild Pack Squad', '294b2aa7-cb46-46bd-8241-69b26d73aa2d', 'https://scryfall.com/card/om1/11/wild-pack-squad?utm_source=api'),
  ('Freya, Queen of the Valkyries', 'Iroas, God of Victory', '36041cf2-159f-4809-9377-930ac4db545f', 'https://scryfall.com/card/sld/2215/iroas-god-of-victory?utm_source=api'),
  ('Friends to the End', 'Twinflame', '83cf1169-5853-4332-b897-7b17d72d76ab', 'https://scryfall.com/card/sld/1810/twinflame?utm_source=api'),
  ('Full-Throttle Fanatic', 'Taxi Driver', 'a17a92f7-e95c-4d0e-a43e-7e6b41a59139', 'https://scryfall.com/card/om1/80/taxi-driver?utm_source=api'),
  ('Gaia''s Dark Hammer', 'Colossus Hammer', '8ec03b88-8d3a-4a32-8b7c-7da59b0c03d0', 'https://scryfall.com/card/sld/1866/colossus-hammer?utm_source=api'),
  ('Galaxy Sword', 'Sword of Forge and Frontier', 'c6331ce3-21f7-4784-80fe-df1f541a4c46', 'https://scryfall.com/card/sld/2817/sword-of-forge-and-frontier?utm_source=api'),
  ('Galvanized Workforce', 'Angry Rabble', 'cf6dc79e-840c-4d47-8f94-c8623528acd2', 'https://scryfall.com/card/om1/81/angry-rabble?utm_source=api'),
  ('Garfield and Odie, Best Buds', 'Rin and Seri, Inseparable', '28c46eb7-bdfc-44b9-b7e9-b073260851f0', 'https://scryfall.com/card/sld/2668/rin-and-seri-inseparable?utm_source=api'),
  ('Garnet Til Alexandros 17th', 'Loran of the Third Path', 'b3d81980-76f2-44e2-b1c9-01e30c726312', 'https://scryfall.com/card/fca/24/loran-of-the-third-path?utm_source=api'),
  ('Gary, the Snail', 'Toxrill, the Corrosive', 'c71b2325-bde6-4364-a93b-8477ffeb25d8', 'https://scryfall.com/card/sld/1929/toxrill-the-corrosive?utm_source=api'),
  ('Generous Betty Wray', 'Silver Sable, Mercenary Leader', '40b82dee-98c7-4b86-88b8-28388cd0331f', 'https://scryfall.com/card/om1/12/silver-sable-mercenary-leader?utm_source=api'),
  ('Ghal Maraz, the Great Shatterer', 'Loxodon Warhammer', 'dba35ac5-7ad3-488a-a006-6b9a1d54eea5', 'https://scryfall.com/card/sld/1034/loxodon-warhammer?utm_source=api'),
  ('Ghazghkull, Prophet of the Waaagh!', 'Zurgo Helmsmasher', '6c48d888-9f5d-43f4-adbd-61dbdba09260', 'https://scryfall.com/card/sld/1028/zurgo-helmsmasher?utm_source=api'),
  ('Ghidorah, King of the Cosmos', 'Illuna, Apex of Wishes', '08daa30f-7ce0-4a72-b539-fbb0c585fd73', 'https://scryfall.com/card/iko/379/illuna-apex-of-wishes?utm_source=api'),
  ('Ghost Trap', 'Soul-Guide Lantern', '1b5e6560-ff2e-4475-96cb-63f64c8a86db', 'https://scryfall.com/card/sld/871/soul-guide-lantern?utm_source=api'),
  ('Ghostbuster''s Patch', 'Boros Charm', '2679d0dd-ba30-4a1c-b6a0-b3ac6c790496', 'https://scryfall.com/card/sld/1771/boros-charm?utm_source=api'),
  ('Giant of Babil', 'Traxos, Scourge of Kroog', 'c1c78144-b335-4d22-a668-9173ab6a0d04', 'https://scryfall.com/card/fca/20/traxos-scourge-of-kroog?utm_source=api'),
  ('Giantcraft Helm', 'Doc Ock''s Tentacles', 'a5a18764-eb29-4bd8-a2e9-0ce55f4f6c88', 'https://scryfall.com/card/om1/167/doc-ocks-tentacles?utm_source=api'),
  ('Gigan, Cyberclaw Terror', 'Gyruda, Doom of Depths', '25eaa977-ca85-4f8d-8be5-9297a3edb14f', 'https://scryfall.com/card/iko/384/gyruda-doom-of-depths?utm_source=api'),
  ('Gilgamesh, Weapon Collector', 'Godo, Bandit Warlord', 'f890d51a-dc90-4179-8423-4738a72a527c', 'https://scryfall.com/card/fca/13/godo-bandit-warlord?utm_source=api'),
  ('Gimme, Gimme, Gimme!', 'Shiny Impetus', 'aae76e5c-f5e0-4d18-b465-e6a829be908a', 'https://scryfall.com/card/sld/7165/shiny-impetus?utm_source=api'),
  ('Glenn, the Voice of Calm', 'Gregor, Shrewd Magistrate', '0b64da77-ca1c-427b-b48b-b919f0fe08e9', 'https://scryfall.com/card/sld/145/gregor-shrewd-magistrate?utm_source=api'),
  ('Glittering Caves of Aglarond', 'Gemstone Caverns', 'c0adbddc-b070-4c5f-afe0-0474c72a9251', 'https://scryfall.com/card/ltc/394z/gemstone-caverns?utm_source=api'),
  ('Gloria, the Great Armorer', 'Araña, Heart of the Spider', 'a16037f2-a0f6-465d-8d6e-cec34b4a6320', 'https://scryfall.com/card/om1/138/ara%C3%B1a-heart-of-the-spider?utm_source=api'),
  ('Goben, Gene-Splice Savant', 'Norman Osborn', 'aa5b06a4-90c3-45e7-ab83-cb5c96ded21d', 'https://scryfall.com/card/om1/30/norman-osborn-green-goblin?utm_source=api'),
  ('Godzilla, Doom Inevitable', 'Yidaro, Wandering Monster', '6c0e22f2-f0f3-43e6-87c5-c543032112d8', 'https://scryfall.com/card/iko/375/yidaro-wandering-monster?utm_source=api'),
  ('Godzilla, King of the Monsters', 'Zilortha, Strength Incarnate', '2dba8d8d-891e-482e-8014-879f701d0619', 'https://scryfall.com/card/iko/275/zilortha-strength-incarnate?utm_source=api'),
  ('Godzilla, Primeval Champion', 'Titanoth Rex', '8656a32b-eb95-402b-9daf-0b6d876b4b13', 'https://scryfall.com/card/iko/377/titanoth-rex?utm_source=api'),
  ('Golbez, Clad In Darkness', 'Syr Konrad, the Grim', '14c3ff84-1e82-4606-a433-869fc52cc382', 'https://scryfall.com/card/fca/10/syr-konrad-the-grim?utm_source=api'),
  ('Gore Magala, Dark Eclipse', 'Razaketh, the Foulblooded', '136c9ecb-59b4-4ef6-bcb2-7b8d3df3ee75', 'https://scryfall.com/card/sld/2251/razaketh-the-foulblooded?utm_source=api'),
  ('Goro Rel, Scourge to Spiders', 'Spider-Slayer, Hatred Honed', 'ca68f436-2522-4007-87bf-2669c7743db0', 'https://scryfall.com/card/om1/168/spider-slayer-hatred-honed?utm_source=api'),
  ('Grandma''s Scroll', 'Merchant Scroll', '86cebe2a-95e7-4f22-99cc-e805aeaf347e', 'https://scryfall.com/card/sld/2824/merchant-scroll?utm_source=api'),
  ('Green Dragon Inn', 'Homeward Path', 'cb8ec2e4-8223-4172-8f2c-37c918a573fa', 'https://scryfall.com/card/ltc/395z/homeward-path?utm_source=api'),
  ('Grimm Fate', 'Beast Within', '7735eeba-693b-47e2-bd51-414379cf1016', 'https://scryfall.com/card/mar/75/beast-within?utm_source=api'),
  ('Gromp', 'Spore Frog', '97db6c39-e690-49b6-93a6-e51b8dfad10b', 'https://scryfall.com/card/sld/696/spore-frog?utm_source=api'),
  ('Guile, Sonic Soldier', 'Immard, the Stormcleaver', '104f65d3-bedb-4dc5-a5dd-8ab9fe796af4', 'https://scryfall.com/card/sld/434/immard-the-stormcleaver?utm_source=api'),
  ('Hades Grip', 'Sulfuric Vortex', '7652f328-e142-494b-a869-772ced10c26a', 'https://scryfall.com/card/sld/2210/sulfuric-vortex?utm_source=api'),
  ('Hadoken', 'Lightning Bolt', '4457ed35-7c10-48c8-9776-456485fdf070', 'https://scryfall.com/card/sld/675/lightning-bolt?utm_source=api'),
  ('Hang In There', 'Ponder', '02090581-61aa-4348-ad57-451be8ee91c2', 'https://scryfall.com/card/sld/2670/ponder?utm_source=api'),
  ('Harker''s Journal', 'Investigator''s Journal', '22e0e822-c4aa-4ec1-b7e4-0c1c869ef71b', 'https://scryfall.com/card/vow/345/investigators-journal?utm_source=api'),
  ('Hawkins National Laboratory', 'Havengul Laboratory', 'e71ac446-02a4-4468-8d29-f28b21617665', 'https://scryfall.com/card/sld/609/havengul-laboratory-havengul-mystery?utm_source=api'),
  ('He-Man, Champion of Eternia', 'Winota, Joiner of Forces', '02598a35-1b11-4abe-89cd-fc44c8c36c15', 'https://scryfall.com/card/sld/2768/winota-joiner-of-forces?utm_source=api'),
  ('Heart of the Explorer', 'Search for Azcanta', 'f74c4d96-bc4a-4d32-9519-a753d192144e', 'https://scryfall.com/card/sld/1502/search-for-azcanta-azcanta-the-sunken-ruin?utm_source=api'),
  ('Heart of the Mountain', 'Arcane Signet', '0bc7f093-bef0-4f1a-852c-4b75ebf54838', 'https://scryfall.com/card/sld/916/arcane-signet?utm_source=api'),
  ('Heaven-Sent Marvel', 'Archangel of Thune', '4f2d4538-dc1d-4c09-964b-b0d7c240fb7d', 'https://scryfall.com/card/mar/41/archangel-of-thune?utm_source=api'),
  ('Helm''s Deep', 'Shinka, the Bloodsoaked Keep', '255b937f-c9c9-4ae9-815e-17418eba0602', 'https://scryfall.com/card/ltc/404z/shinka-the-bloodsoaked-keep?utm_source=api'),
  ('Henneth Annûn', 'Reflecting Pool', '67f43ac6-2a58-4b53-b5d7-0330e2a252e2', 'https://scryfall.com/card/ltc/403z/reflecting-pool?utm_source=api'),
  ('Heralds of the Shredder', 'Vigor', '70787d8b-0a40-43ea-837a-9617dc13e7e5', 'https://scryfall.com/card/tmc/53/vigor?utm_source=api'),
  ('Hero of Hoarfrost Reach', 'Archaeomancer', 'a91a3266-cadd-47a0-9b20-160307f14c07', 'https://scryfall.com/card/sld/2242/archaeomancer?utm_source=api'),
  ('Hero of Light', 'Adeline, Resplendent Cathar', '38515f89-348b-4cf3-b7bd-1f6fe4ce2fba', 'https://scryfall.com/card/fca/1/adeline-resplendent-cathar?utm_source=api'),
  ('Herugrim, Sword of Rohan', 'Sword of Hearth and Home', '913e6182-706a-4872-8c8a-e146b0ae0738', 'https://scryfall.com/card/ltc/384z/sword-of-hearth-and-home?utm_source=api'),
  ('Hex of Undeath', 'Behold the Sinister Six!', '6fa27f8a-bade-460f-853a-abc1c05c946a', 'https://scryfall.com/card/om1/57/behold-the-sinister-six!?utm_source=api'),
  ('Hide in Mundanity', 'Spider-Man No More', '163f1fce-70c8-44e3-a679-f97d52cd1e9a', 'https://scryfall.com/card/om1/31/spider-man-no-more?utm_source=api'),
  ('Holga, Relentless Rager', 'Jurin, Leading the Charge', 'de384867-8bb4-4edf-b542-970538718fdd', 'https://scryfall.com/card/sld/1240/jurin-leading-the-charge?utm_source=api'),
  ('Hope''s Aero Magic', 'Cyclonic Rift', 'd75b9c82-1b49-4c3e-a1b5-aeef57d6644b', 'https://scryfall.com/card/sld/1869/cyclonic-rift?utm_source=api'),
  ('Hugo Kupka', 'Bruse Tarl, Boorish Herder', 'e39a1f6b-6b13-4a8b-ac0c-63ede4636812', 'https://scryfall.com/card/fca/50/bruse-tarl-boorish-herder?utm_source=api'),
  ('Humongous Fungus', 'Corpsejack Menace', 'ca0cc02b-b106-4eca-9388-d4b48dd3be49', 'https://scryfall.com/card/tmc/56/corpsejack-menace?utm_source=api'),
  ('Hunger of the Ancient One', 'Exquisite Blood', '8f933fae-6c0c-42d7-a817-14760d8285cd', 'https://scryfall.com/card/sld/206/exquisite-blood?utm_source=api'),
  ('Huu''s Reach', 'Kodama''s Reach', '1593ea18-2f2f-4ab4-83fb-6ccc0bec8a90', 'https://scryfall.com/card/sld/2294/kodamas-reach?utm_source=api'),
  ('I Hate Mondays', 'Beast Within', '7735eeba-693b-47e2-bd51-414379cf1016', 'https://scryfall.com/card/sld/2671/beast-within?utm_source=api'),
  ('Ian, Convalescent Charmer', 'Tasigur, the Golden Fang', '837e3fde-241f-4826-ad04-f146fdcf2278', 'https://scryfall.com/card/sld/1396%E2%98%85/tasigur-the-golden-fang?utm_source=api'),
  ('Ifrit', 'Fury', 'fbf9f8c5-849f-45d5-8129-5fc683c21a04', 'https://scryfall.com/card/sld/7007/fury?utm_source=api'),
  ('Indominus Rex', 'Polyraptor', 'e47e3a40-f51f-41ed-8e7c-06200a2abc22', 'https://scryfall.com/card/sld/1391%E2%98%85/polyraptor?utm_source=api'),
  ('Inigo, Avenging Swordsman', 'Samut, Voice of Dissent', 'b1eee275-5106-4c8d-a497-d7945ad81d74', 'https://scryfall.com/card/sld/1451/samut-voice-of-dissent?utm_source=api'),
  ('Inn of the Prancing Pony', 'Pillar of the Paruns', '677b8ce7-f922-4ee3-b311-f199da9b352b', 'https://scryfall.com/card/ltc/402z/pillar-of-the-paruns?utm_source=api'),
  ('Intergalactic Wrestling', 'Possibility Storm', '8586169f-cb8c-4424-ba64-a7c1cc00680e', 'https://scryfall.com/card/sld/7073/possibility-storm?utm_source=api'),
  ('Iron Spider, Civil Warrior', 'Alibou, Ancient Witness', 'e5e8e116-10fe-48b0-b3d8-6edb39bd5f90', 'https://scryfall.com/card/mar/39/alibou-ancient-witness?utm_source=api'),
  ('Isengard, Saruman''s Fortress', 'Boseiju, Who Shelters All', '36937483-30cb-449a-8028-75017a124922', 'https://scryfall.com/card/ltc/389z/boseiju-who-shelters-all?utm_source=api'),
  ('Janai and Hoppy, Roofskippers', 'Spider-Girl, Legacy Hero', 'd459b3f5-a18c-4c17-a855-dc147f7c2161', 'https://scryfall.com/card/om1/139/spider-girl-legacy-hero?utm_source=api'),
  ('Joe Fixit''s Expertise', 'Rishkar''s Expertise', '97407cd0-2bd2-4074-94d3-4ec3d243fa78', 'https://scryfall.com/card/sld/2597/rishkars-expertise?utm_source=api'),
  ('Jonathan Harker', 'Jacob Hauken, Inspector', '16d2a56a-7181-4ef3-866b-10dd8615d9e9', 'https://scryfall.com/card/vow/332/jacob-hauken-inspector-haukens-insight?utm_source=api'),
  ('Joo Dee, Public Servant', 'Sakashima of a Thousand Faces', '8ecdaf4b-4442-42da-9714-4257a83faf50', 'https://scryfall.com/card/tle/18/sakashima-of-a-thousand-faces?utm_source=api'),
  ('Joshua Graham, Burned Man', 'Isshin, Two Heavens as One', '65114758-9a75-43a7-96e8-0aa68faa6b24', 'https://scryfall.com/card/sld/2459/isshin-two-heavens-as-one?utm_source=api'),
  ('Joshua Rosfield', 'Rograkh, Son of Rohgahh', '584cee10-f18c-4633-95cc-f2e7a11841ac', 'https://scryfall.com/card/pf25/11/rograkh-son-of-rohgahh?utm_source=api'),
  ('Junimo Farmhands', 'Sylvan Caryatid', '13d4c46b-c2d6-44cc-a252-4a991d471854', 'https://scryfall.com/card/sld/7189/sylvan-caryatid?utm_source=api'),
  ('KAITO, Mysterious Maestro', 'Jace, Unraveler of Secrets', 'ac29873e-28c3-4933-b427-61d34ff0afcd', 'https://scryfall.com/card/sld/1590/jace-unraveler-of-secrets?utm_source=api'),
  ('Katsuichi''s Peace', 'Felidar Retreat', '16629f59-bae8-4c19-bf50-443eb0ed6856', 'https://scryfall.com/card/sld/2378/felidar-retreat?utm_source=api'),
  ('Kavaero, Mind-Bitten', 'Superior Spider-Man', '636cc915-9d1b-4ffe-9e74-795b78663911', 'https://scryfall.com/card/om1/140/superior-spider-man?utm_source=api'),
  ('Kazuo, Ruthless Rival', 'Shocker, Unshakable', '564dac59-97f7-4988-9f30-d82a891e29ef', 'https://scryfall.com/card/om1/83/shocker-unshakable?utm_source=api'),
  ('Kefka Palazzo', 'Purphoros, God of the Forge', '4fdbbec2-e921-4b63-958d-f9ba1e417197', 'https://scryfall.com/card/fca/14/purphoros-god-of-the-forge?utm_source=api'),
  ('Kefka''s Tower', 'Bolas''s Citadel', '2bd111bb-ce02-414c-b5b7-e0e037d8d96b', 'https://scryfall.com/card/fca/7/bolass-citadel?utm_source=api'),
  ('Ken, Burning Brawler', 'Aisha of Sparks and Smoke', 'eae3e762-dacd-4bd2-923c-3abb5ceb729a', 'https://scryfall.com/card/sld/430/aisha-of-sparks-and-smoke?utm_source=api'),
  ('Kephon, Rage Incubator', 'Stegron the Dinosaur Man', '5c94b616-8edf-465c-b316-4599df95c52a', 'https://scryfall.com/card/om1/84/stegron-the-dinosaur-man?utm_source=api'),
  ('Khan, Engineered Evil', 'Sheoldred, the Apocalypse', '34f34409-326d-4994-a0ea-1a69aa278f03', 'https://scryfall.com/card/sds/11/sheoldred-the-apocalypse?utm_source=api'),
  ('Killer Rabbit of Caerbannog', 'Kezzerdrix', '1523671c-0cf4-442c-a5f8-c74ae31016e6', 'https://scryfall.com/card/sld/826/kezzerdrix?utm_source=api'),
  ('King Caesar, Ancient Guardian', 'Huntmaster Liger', '38f5e6bf-18a3-4ff3-9726-a25a9715a2d9', 'https://scryfall.com/card/iko/370/huntmaster-liger?utm_source=api'),
  ('King Caesar, Awoken Titan', 'Snapdax, Apex of the Hunt', 'b2b78623-5a10-4ef7-b983-3d82478269c3', 'https://scryfall.com/card/iko/381/snapdax-apex-of-the-hunt?utm_source=api'),
  ('King of the Coldblood Curse', 'Lizard, Connors''s Curse', '48d1b217-b068-468c-bc6c-4bef9e44cc6e', 'https://scryfall.com/card/om1/108/lizard-connorss-curse?utm_source=api'),
  ('Kings Bay Clock Tower', 'Midnight Clock', 'c68faebc-b2cd-461b-b93e-e1fcd4816810', 'https://scryfall.com/card/sld/2217/midnight-clock?utm_source=api'),
  ('Kitezh, Sunken City', 'Academy Ruins', 'a3da7d5b-2c2b-45fe-b9c5-413b8c8fc0a2', 'https://scryfall.com/card/sld/1506/academy-ruins?utm_source=api'),
  ('Kivni, Orb Weaver', 'Scarlet Spider, Kaine', '4ec8a5ea-b750-4711-8843-2bc98f4ce060', 'https://scryfall.com/card/om1/141/scarlet-spider-kaine?utm_source=api'),
  ('Knife Trick', 'Pumpkin Bombardment', '37827e84-9f5f-49ed-b939-0cf80dac82e7', 'https://scryfall.com/card/om1/142/pumpkin-bombardment?utm_source=api'),
  ('Knights of San d''Oria', 'Ranger-Captain of Eos', 'cada3481-cc2b-4412-b9b5-0436af53aad2', 'https://scryfall.com/card/fca/2/ranger-captain-of-eos?utm_source=api'),
  ('Knowby''s Incantation', 'Zombie Apocalypse', '8241277d-654f-4985-9d49-a22c1e59eec2', 'https://scryfall.com/card/sld/1354/zombie-apocalypse?utm_source=api'),
  ('Knuckles''s Gloves', 'The Reaver Cleaver', '37a2a31d-51e6-4c07-b4c2-b206ad40eb42', 'https://scryfall.com/card/sld/2095/the-reaver-cleaver?utm_source=api'),
  ('Krang''s Android', 'Triskelion', '74f67dcf-5afb-45aa-8d4b-3cdb23f6f2a1', 'https://scryfall.com/card/sld/2371/triskelion?utm_source=api'),
  ('Kratos'' Rage', 'Pyrohemia', '9ac57a10-3402-4656-9079-f713884cde35', 'https://scryfall.com/card/sld/2211/pyrohemia?utm_source=api'),
  ('Kraza, the Swarm as One', 'Spider-Punk', '03bf7a90-78c1-4e83-8553-e22d85e49876', 'https://scryfall.com/card/om1/85/spider-punk?utm_source=api'),
  ('Kroble, Envoy of the Bog', 'Spider-Man Noir', '2efd6494-c5e1-41de-bc6e-8490ff046cd1', 'https://scryfall.com/card/om1/59/spider-man-noir?utm_source=api'),
  ('Krobus', 'Academy Manufactor', 'f36d1d8b-8303-44a9-ab56-531931641ea2', 'https://scryfall.com/card/sld/7188/academy-manufactor?utm_source=api'),
  ('Kuja, Mage Manufacturer', 'Inalla, Archmage Ritualist', '21bdba6e-3f9d-4ead-8212-0cbb0ce7f8cc', 'https://scryfall.com/card/fca/52/inalla-archmage-ritualist?utm_source=api'),
  ('Kumonosu, the Watchful', 'SP//dr, Piloted by Peni', '722ab6e4-a2e0-4aaa-a050-7b6436e22b40', 'https://scryfall.com/card/om1/143/spdr-piloted-by-peni?utm_source=api'),
  ('Kushala Daora''s Fury', 'Snap', 'ac914d98-221e-426c-8a50-342896b15f9e', 'https://scryfall.com/card/sld/2247/snap?utm_source=api'),
  ('La Madre Tierra', 'Xenagos, God of Revels', 'cb15a8dd-57fe-466f-847e-66476b690a1f', 'https://scryfall.com/card/sld/2061/xenagos-god-of-revels?utm_source=api'),
  ('La abuela, siempre generosa', 'Tireless Provisioner', 'ab8d5f5c-1976-4f77-8ed2-8d28ee666741', 'https://scryfall.com/card/sld/2057/tireless-provisioner?utm_source=api'),
  ('La abundancia de Yucahú', 'Sylvan Library', '92eed395-62ca-4293-882b-8565c40daab5', 'https://scryfall.com/card/sld/2058/sylvan-library?utm_source=api'),
  ('La danza del pueblo', 'Expressive Iteration', 'c7aecca5-2f67-4245-ab2d-e723d8b23a67', 'https://scryfall.com/card/sld/2060/expressive-iteration?utm_source=api'),
  ('Lady Loki''s Manifestation', 'Titan of Littjara', 'f62250c6-0832-46c8-a800-806589504f5f', 'https://scryfall.com/card/msc/335/titan-of-littjara?utm_source=api'),
  ('Lagiacrus, Lord of the Seas', 'Nezahal, Primal Tide', 'c45e96cb-2539-4e00-9fff-782a182c2f4b', 'https://scryfall.com/card/sld/2236/nezahal-primal-tide?utm_source=api'),
  ('Lavaborn Goblins', 'Raging Goblinoids', 'c807b53f-2917-41a0-812c-57240b623365', 'https://scryfall.com/card/om1/86/raging-goblinoids?utm_source=api'),
  ('Lavabrink Repels the Magmaloth', 'Maximum Carnage', '7351fca5-8672-4ba3-a015-bd4b6b289efc', 'https://scryfall.com/card/om1/87/maximum-carnage?utm_source=api'),
  ('Lazlo, Enthusiastic Accuser', 'J. Jonah Jameson', 'de861715-fd0b-493e-9a7c-c470a23044c0', 'https://scryfall.com/card/om1/88/j-jonah-jameson?utm_source=api'),
  ('Len and Rin, Harmony Incarnate', 'The Royal Scions', '4ecde8d1-e4ec-4bd9-8a80-49885b032557', 'https://scryfall.com/card/sld/1600/the-royal-scions?utm_source=api'),
  ('Leo''s Katana', 'Sword of Sinew and Steel', 'ccab4509-f189-4610-9597-547e7f6b0775', 'https://scryfall.com/card/pza/18/sword-of-sinew-and-steel?utm_source=api'),
  ('Leyline Weaver', 'Spider Manifestation', '8281f2b9-e81b-48da-812a-8713b2adf8ab', 'https://scryfall.com/card/om1/144/spider-manifestation?utm_source=api'),
  ('Lifelong Friendship', 'Eladamri''s Call', '4acb6612-54e8-428d-acb6-c7259a5ad6a8', 'https://scryfall.com/card/tle/48/eladamris-call?utm_source=api'),
  ('Lightning, Lone Commando', 'Isshin, Two Heavens as One', '65114758-9a75-43a7-96e8-0aa68faa6b24', 'https://scryfall.com/card/fca/54/isshin-two-heavens-as-one?utm_source=api'),
  ('Linda, Kandarian Queen', 'Varina, Lich Queen', '9859fbca-60c3-4a57-a377-51b56f03894f', 'https://scryfall.com/card/sld/1355/varina-lich-queen?utm_source=api'),
  ('Lively Leap', 'Thwip!', 'f7d11254-b48a-4016-a035-c0d6642fdfae', 'https://scryfall.com/card/om1/13/thwip!?utm_source=api'),
  ('Lofi Cat', 'Felidar Guardian', '33869ba6-13e5-4e48-8963-92f7965648fb', 'https://scryfall.com/card/sld/2821/felidar-guardian?utm_source=api'),
  ('Loki''s Double', 'Spark Double', '8dcb35e5-ae44-455f-86e3-4a77d496ff34', 'https://scryfall.com/card/msc/337/spark-double?utm_source=api'),
  ('Lost in Littjara', 'The Clone Saga', '0f0282c6-aceb-4879-8ec8-482d0501204a', 'https://scryfall.com/card/om1/33/the-clone-saga?utm_source=api'),
  ('Luca Stadium', 'Strixhaven Stadium', '2ed0c6fc-b8b4-47da-a04b-1d995bdeecb0', 'https://scryfall.com/card/fca/63/strixhaven-stadium?utm_source=api'),
  ('Lucas, the Sharpshooter', 'Bjorna, Nightfall Alchemist', 'c880fbdc-bdd9-4f80-81d4-e3e1124f76ca', 'https://scryfall.com/card/sld/344/bjorna-nightfall-alchemist?utm_source=api'),
  ('Lucille', 'Gisa''s Favorite Shovel', '9c298c7b-9c63-4a66-a0fc-977491b623c7', 'https://scryfall.com/card/sld/581/gisas-favorite-shovel?utm_source=api'),
  ('Lucky Purple Memento', 'Puca''s Mischief', 'a8e6655c-e63f-4a60-98f6-9d5bf8631488', 'https://scryfall.com/card/sld/923/pucas-mischief?utm_source=api'),
  ('Lucy Westenra', 'Innocent Traveler', '7950a7ff-7c2e-40fe-b64a-324f4fbcf528', 'https://scryfall.com/card/vow/336/innocent-traveler-malicious-invader?utm_source=api'),
  ('Luis, Pompous Pillager', 'Morlun, Devourer of Spiders', '273ad15c-366a-4691-978b-d6028b57005a', 'https://scryfall.com/card/om1/60/morlun-devourer-of-spiders?utm_source=api'),
  ('Luka, the Traveling Sound', 'Liliana of the Dark Realms', '92301066-8904-41bc-84bd-4aa286cbab9c', 'https://scryfall.com/card/sld/1593/liliana-of-the-dark-realms?utm_source=api'),
  ('Lunch 1:00 PM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2548/food?utm_source=api'),
  ('Lórien Brooch', 'Trailblazer''s Boots', '634d5009-cbf3-44cb-8c15-7057f501a210', 'https://scryfall.com/card/ltr/398/trailblazers-boots?utm_source=api'),
  ('MEIKO, Explosive Entertainer', 'Chandra, Flamecaller', '0c2a9131-f3d7-4f71-8bcc-3c169574b2e3', 'https://scryfall.com/card/sld/807/chandra-flamecaller?utm_source=api'),
  ('Magus Sisters', 'Endurance', 'c85d824b-c190-4d04-ab99-918ad0e6516c', 'https://scryfall.com/card/sld/7008/endurance?utm_source=api'),
  ('Makari the Lucky Grot', 'Krenko, Tin Street Kingpin', 'e8065e1d-e937-4b56-8011-78f0d07328a0', 'https://scryfall.com/card/sld/1027/krenko-tin-street-kingpin?utm_source=api'),
  ('Makdee and Itla, Skysnarers', 'Spider-Woman, Stunning Savior', 'be2b9c6d-4ecb-49ec-b276-4aa93c5dfc00', 'https://scryfall.com/card/om1/145/spider-woman-stunning-savior?utm_source=api'),
  ('Malcolm''s Mercurial Mirth', 'Tasha''s Hideous Laughter', 'e352f5b9-6406-4914-bc79-f24608be6bc9', 'https://scryfall.com/card/sld/1395%E2%98%85/tashas-hideous-laughter?utm_source=api'),
  ('Man Ray, Eco Avenger', 'Deepglow Skate', 'debce64a-18bd-42f5-9e85-158c2242e9e9', 'https://scryfall.com/card/sld/2362/deepglow-skate?utm_source=api'),
  ('Man-At-Arms, Master Tactician', 'Bruenor Battlehammer', 'ea7de96f-db69-421d-a951-ffaeac140379', 'https://scryfall.com/card/sld/2771/bruenor-battlehammer?utm_source=api'),
  ('Man-E-Faces, Actor of Eternia', 'Sakashima the Impostor', 'a7243d25-22a2-4df5-adaf-1f40f5330ec1', 'https://scryfall.com/card/sld/2784/sakashima-the-impostor?utm_source=api'),
  ('Man-Thing, Marsh Protector', 'Bristly Bill, Spine Sower', 'd3b2d8a2-d3bc-448c-9cf6-6bead6010c28', 'https://scryfall.com/card/sld/2621/bristly-bill-spine-sower?utm_source=api'),
  ('Marauding Mutagen', 'Acidic Slime', '21f45043-5419-4019-8b6c-e5294bd5f549', 'https://scryfall.com/card/tmc/48/acidic-slime?utm_source=api'),
  ('Margot, On the Case', 'Wraith, Vicious Vigilante', '38684c31-e8c6-4825-8740-1a3d34b58b39', 'https://scryfall.com/card/om1/146/wraith-vicious-vigilante?utm_source=api'),
  ('Master Emerald Shrine', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/7030/command-tower?utm_source=api'),
  ('Master Weaver, Web Protector', 'Arasta of the Endless Web', '695eea46-1535-48c5-bbb6-0b8379e77bfc', 'https://scryfall.com/card/mar/32/arasta-of-the-endless-web?utm_source=api'),
  ('Master Xande', 'Venser, Shaper Savant', '0f41cefc-d6ff-4db7-ba35-502b7e081de1', 'https://scryfall.com/card/fca/6/venser-shaper-savant?utm_source=api'),
  ('Max, the Daredevil', 'Elmar, Ulvenwald Informant', '5a35201d-e9b1-433a-bb70-3280ceedbcd6', 'https://scryfall.com/card/sld/345/elmar-ulvenwald-informant?utm_source=api'),
  ('Mayor Tong of Chin Village', 'Drannith Magistrate', 'aadd10d0-6dd0-4bdc-8d93-ff08e29a5863', 'https://scryfall.com/card/tle/2/drannith-magistrate?utm_source=api'),
  ('Mechagodzilla, Battle Fortress', 'Hangarback Walker', 'dde55256-5259-44e7-a267-fca45a7f0d04', 'https://scryfall.com/card/plg20/2/hangarback-walker?utm_source=api'),
  ('Mechagodzilla, the Weapon', 'Crystalline Giant', '49a46cfa-f2e9-4718-a6cb-47dbb0792b56', 'https://scryfall.com/card/prm/80937/crystalline-giant?utm_source=api'),
  ('Meduseld, Golden Hall of Edoras', 'Castle Ardenvale', 'f8f4fc60-725d-46d8-8e8f-e68e00d20589', 'https://scryfall.com/card/ltc/391z/castle-ardenvale?utm_source=api'),
  ('Memories of Nibelheim', 'Stroke of Midnight', '9a107e48-3d50-4941-95b1-10f2b29a4245', 'https://scryfall.com/card/fca/26/stroke-of-midnight?utm_source=api'),
  ('Merata, Neuron Hacker', 'Lady Octopus, Inspired Inventor', '8e51fdb8-4f83-4e94-b36c-40a501075ecb', 'https://scryfall.com/card/om1/34/lady-octopus-inspired-inventor?utm_source=api'),
  ('Merciless Poisoning', 'Toxic Deluge', 'afaef788-34d1-460b-b884-9d7ae6ddeb18', 'https://scryfall.com/card/sld/1860/toxic-deluge?utm_source=api'),
  ('Mermaid''s Pendant', 'Wedding Ring', '0c34e962-99d9-4163-b852-4f61886546aa', 'https://scryfall.com/card/sld/2802/wedding-ring?utm_source=api'),
  ('Meteorfall', 'Star of Extinction', '48220e6c-5752-46e0-9b7f-f0eef274d929', 'https://scryfall.com/card/sld/1862/star-of-extinction?utm_source=api'),
  ('Miasmic Mist', 'Sandman''s Quicksand', 'f2b376d2-a2f4-4d23-a1fb-eb7b6ebd0b7a', 'https://scryfall.com/card/om1/62/sandmans-quicksand?utm_source=api'),
  ('Michonne, Ruthless Survivor', 'Enkira, Hostile Scavenger', '558fd7a9-9b39-4c82-b909-5febf55dc010', 'https://scryfall.com/card/sld/146/enkira-hostile-scavenger?utm_source=api'),
  ('Mike, the Dungeon Master', 'Othelm, Sigardian Outcast', '4ee401bf-dc86-41a9-84f9-57aa0a314d08', 'https://scryfall.com/card/sld/346/othelm-sigardian-outcast?utm_source=api'),
  ('Miku''s Spark', 'Chandra''s Ignition', 'f61680da-606e-4d16-b0a0-361aa5210901', 'https://scryfall.com/card/sld/1594%E2%98%85/chandras-ignition?utm_source=api'),
  ('Miku, Child of Song', 'Child of Alara', '70dbe8a9-505d-41c2-9b5b-a991d13ab459', 'https://scryfall.com/card/sld/1599/child-of-alara?utm_source=api'),
  ('Miku, Divine Diva', 'Elspeth Tirel', '5f815e69-fdd6-4186-9317-25f5c7e0b08e', 'https://scryfall.com/card/sld/1585/elspeth-tirel?utm_source=api'),
  ('Miku, Font of Pop', 'Giada, Font of Hope', '48e6d3d8-2f27-4017-acdd-40bce8cdbc02', 'https://scryfall.com/card/sld/1586/giada-font-of-hope?utm_source=api'),
  ('Miku, Lost but Singing', 'Azusa, Lost but Seeking', '6c2c8bf3-9bf8-4a86-89d3-3bb36260dc51', 'https://scryfall.com/card/sld/1597%E2%98%85/azusa-lost-but-seeking?utm_source=api'),
  ('Miku, Queen Electric', 'Brago, King Eternal', 'fcb0c7db-bd07-4c25-b7f8-b6c207e4f6be', 'https://scryfall.com/card/sld/1601/brago-king-eternal?utm_source=api'),
  ('Miku, Song of the People', 'Trostani, Selesnya''s Voice', 'e94ef397-f5c5-4b8d-ae27-528352fa1d1e', 'https://scryfall.com/card/sld/2443/trostani-selesnyas-voice?utm_source=api'),
  ('Miku, Voice Over All', 'Shalai, Voice of Plenty', 'a0c47ab6-dfb4-46ee-a3f7-9e1521b4bb4b', 'https://scryfall.com/card/sld/2433/shalai-voice-of-plenty?utm_source=api'),
  ('Miku, Voice of Power', 'Freyalise, Llanowar''s Fury', '659dfdbf-5e9d-4828-a967-348cb3bcf05a', 'https://scryfall.com/card/sld/1598/freyalise-llanowars-fury?utm_source=api'),
  ('Miku, the Complete Performer', 'Vorinclex, Voice of Hunger', 'dbf0ad03-ab31-49d2-89b1-05b45948a61f', 'https://scryfall.com/card/sld/2439/vorinclex-voice-of-hunger?utm_source=api'),
  ('Miku, the Renowned', 'Feather, the Redeemed', 'aa219936-661b-4ccb-8741-78b70cff2b1a', 'https://scryfall.com/card/sld/1602%E2%98%85/feather-the-redeemed?utm_source=api'),
  ('Mina Harker', 'Thalia, Guardian of Thraben', '9b7f1d05-707c-4ed3-9f0e-8ced1232c2ee', 'https://scryfall.com/card/vow/331/thalia-guardian-of-thraben?utm_source=api'),
  ('Minas Morgul', 'Cabal Coffers', '7358e164-5704-4e78-9b21-6a9bf2a968ce', 'https://scryfall.com/card/ltc/390z/cabal-coffers?utm_source=api'),
  ('Mind Flayer, the Shadow', 'Arvinox, the Mind Flail', '9abecd23-a2d9-43c7-8d01-f8afdc53026e', 'https://scryfall.com/card/sld/340/arvinox-the-mind-flail?utm_source=api'),
  ('Minwu, Rebellion Strategist', 'Mangara, the Diplomat', 'cbcb6d9a-6ae5-4bcd-8013-2b657553764a', 'https://scryfall.com/card/fca/25/mangara-the-diplomat?utm_source=api'),
  ('Miracle Max, Unemployed', 'Marchesa, the Black Rose', '17a59d3d-9e01-48cd-bb4a-3eaaa077751c', 'https://scryfall.com/card/sld/1452/marchesa-the-black-rose?utm_source=api'),
  ('Mirelurk Hatchling', 'Ruin Crab', '8afc00d4-a1c6-4329-af2c-a7f58a0c33e7', 'https://scryfall.com/card/sld/7095/ruin-crab?utm_source=api'),
  ('Mister Sinister, Hubris Unbound', 'Endrek Sahr, Master Breeder', '47a0079f-3544-45bc-a32a-bd93844c8c43', 'https://scryfall.com/card/sld/2620/endrek-sahr-master-breeder?utm_source=api'),
  ('Miyamoto Usagi', 'Baylen, the Haymaker', '73dc28a7-37ac-4b16-aa00-967c9c44d979', 'https://scryfall.com/card/sld/2377/baylen-the-haymaker?utm_source=api'),
  ('Mondo Gecko, Esquire', 'Kediss, Emberclaw Familiar', 'd9c87cc2-943e-49b6-becc-748857549617', 'https://scryfall.com/card/sld/2364/kediss-emberclaw-familiar?utm_source=api'),
  ('Monica, the Marvel', 'Aurelia, the Warleader', '0f5a3a09-2f07-4774-9e0f-e99d9a444166', 'https://scryfall.com/card/mar/86/aurelia-the-warleader?utm_source=api'),
  ('Monkey, Awakened to Emptiness', 'Kibo, Uktabi Prince', '0b9be4fa-5238-4afd-a9f6-f9022e67e5ab', 'https://scryfall.com/card/sld/2401/kibo-uktabi-prince?utm_source=api'),
  ('Morgul-Knife', 'Shadowspear', '8b27326f-e7b8-4a4d-b589-df459246d19a', 'https://scryfall.com/card/ltc/383z/shadowspear?utm_source=api'),
  ('Mothman Egg', 'Mesmeric Orb', '03efb4f3-b8e2-4441-824f-886dc40712c4', 'https://scryfall.com/card/sld/2457/mesmeric-orb?utm_source=api'),
  ('Mothra''s Great Cocoon', 'Mysterious Egg', 'd3b62851-6013-49e5-8808-fa61b1bdfe98', 'https://scryfall.com/card/prm/80939/mysterious-egg?utm_source=api'),
  ('Mothra, Supersonic Queen', 'Luminous Broodmoth', '28c7c816-07e7-42fb-923c-bf149ba28b38', 'https://scryfall.com/card/iko/371/luminous-broodmoth?utm_source=api'),
  ('Mothwing Shroud', 'Web Up', '9b9b086c-d201-4574-a1e9-0d6f8de53d7d', 'https://scryfall.com/card/om1/15/web-up?utm_source=api'),
  ('Mr. Krabs, Penny Pincher', 'Charix, the Raging Isle', 'c38cc5fe-936a-4d61-a816-9be773ae1d02', 'https://scryfall.com/card/sld/1927/charix-the-raging-isle?utm_source=api'),
  ('Mutanimals United', 'Triumph of the Hordes', '3ded0c0c-40ce-4d14-a9a6-b023bc19ee0e', 'https://scryfall.com/card/sld/2366/triumph-of-the-hordes?utm_source=api'),
  ('Mysterious Blood Illness', 'Vampires'' Vengeance', '3a82e724-28f6-430f-a474-ab4276197963', 'https://scryfall.com/card/vow/339/vampires-vengeance?utm_source=api'),
  ('NOT A WOLF', 'Tovolar, Dire Overlord', '45d49831-548a-4a0e-9a18-9f7397913895', 'https://scryfall.com/card/sld/1612/tovolar-dire-overlord-tovolar-the-midnight-scourge?utm_source=api'),
  ('Nargacuga Stalker', 'Grim Haruspex', '72aef1d8-11df-4bc2-af83-907b05df73a8', 'https://scryfall.com/card/sld/2243/grim-haruspex?utm_source=api'),
  ('Nargacuga, Ever-Present Shadow', 'Wasitora, Nekoru Queen', '13fc4168-fcc2-4011-804f-211d5d86b7dd', 'https://scryfall.com/card/sld/2253/wasitora-nekoru-queen?utm_source=api'),
  ('Neach, Pinnacle Pariah', 'Doctor Octopus, Master Planner', '2fecfbef-e521-4025-94ea-451c9abde3de', 'https://scryfall.com/card/om1/148/doctor-octopus-master-planner?utm_source=api'),
  ('Neave Blacktalon', 'Danitha Capashen, Paragon', '4b6377da-83e7-4519-9582-16a9c16b8faa', 'https://scryfall.com/card/sld/1031/danitha-capashen-paragon?utm_source=api'),
  ('Negan, the Cold-Blooded', 'Malik, Grim Manipulator', '416608a1-89a4-44ce-8fd0-fab6b023d3d4', 'https://scryfall.com/card/sld/147/malik-grim-manipulator?utm_source=api'),
  ('Nergigante, Herald of Destruction', 'Vaevictis Asmadi, the Dire', 'c42ce2e9-4dfe-468a-8f41-49e187cb91d4', 'https://scryfall.com/card/sld/2239/vaevictis-asmadi-the-dire?utm_source=api'),
  ('Newfound Adventure', 'Farseek', '495e52e6-4c2b-4574-9474-eadbdcc8b4ac', 'https://scryfall.com/card/fca/45/farseek?utm_source=api'),
  ('Nia, Skysail Storyteller', 'Gwen Stacy', '5f143d87-35fb-40e3-94ae-f85cfff9adb5', 'https://scryfall.com/card/om1/89/gwen-stacy-ghost-spider?utm_source=api'),
  ('Nightfeeder''s Visitation', 'Night''s Whisper', '7ffae8f8-3006-4969-a339-6d30678f87ea', 'https://scryfall.com/card/sld/207/nights-whisper?utm_source=api'),
  ('Nill, Vessel of Valgavoth', 'Tombstone, Career Criminal', '6ad2cbb6-2291-420c-bfc8-ed3f079b59bf', 'https://scryfall.com/card/om1/63/tombstone-career-criminal?utm_source=api'),
  ('Noctis Lucis Caelum', 'Kenrith, the Returned King', 'd209b948-9afb-4fd1-a961-72c87282878c', 'https://scryfall.com/card/fca/23/kenrith-the-returned-king?utm_source=api'),
  ('Noctis''s Death Magic', 'Damn', 'b01d61cc-9844-4191-86a0-f2db6d42d6e5', 'https://scryfall.com/card/sld/1870/damn?utm_source=api'),
  ('Nu and Sumi, Career Criminals', 'Green Goblin, Revenant', '67175889-02f9-4ad8-a9ab-11db44328b67', 'https://scryfall.com/card/om1/149/green-goblin-revenant?utm_source=api'),
  ('Obscura Alleylurkers', 'Doc Ock''s Henchmen', 'ae91c16c-5267-4957-b36c-5aa787fa6b5e', 'https://scryfall.com/card/om1/35/doc-ocks-henchmen?utm_source=api'),
  ('Olx, Mouth to Many Eyes', 'Madame Web, Clairvoyant', 'b1e0841d-b004-40f9-a644-aecb422f6ad5', 'https://scryfall.com/card/om1/36/madame-web-clairvoyant?utm_source=api'),
  ('Opulent Valet', 'News Helicopter', '192dd1e2-b6c2-432a-a1b4-e52ff39b3db2', 'https://scryfall.com/card/om1/169/news-helicopter?utm_source=api'),
  ('Orbital Vibranium Bomb', 'Scourglass', '78541a40-c27a-49c0-aa3e-5a48b97065f0', 'https://scryfall.com/card/msc/318/scourglass?utm_source=api'),
  ('Ork Kommando', 'Merciless Executioner', 'c3c45d50-9038-41df-bb2f-9bc40071845b', 'https://scryfall.com/card/sld/1025/merciless-executioner?utm_source=api'),
  ('Orko, Trollan Magician', 'Delina, Wild Mage', '8d57dadb-c689-4691-b331-aba15daf46ff', 'https://scryfall.com/card/sld/2770/delina-wild-mage?utm_source=api'),
  ('Ororo Borealis', 'Manamorphose', '89c83a6d-f6c8-4984-a888-0db62dfb93b1', 'https://scryfall.com/card/sld/1746/manamorphose?utm_source=api'),
  ('Orphan, Cocoon fal''Cie', 'Muldrotha, the Gravetide', 'e4625704-1d52-44e4-804f-2f45644d76ac', 'https://scryfall.com/card/fca/57/muldrotha-the-gravetide?utm_source=api'),
  ('Orris, Last of the Web Lords', 'Ezekiel Sims, Spider-Totem', '4074e897-82a4-4f57-86c2-4aab3f29ef9b', 'https://scryfall.com/card/om1/110/ezekiel-sims-spider-totem?utm_source=api'),
  ('Osgiliath, Fallen Capital', 'Kor Haven', '276cece9-f9f2-46e6-ae76-daddaa2fb9ab', 'https://scryfall.com/card/ltc/398z/kor-haven?utm_source=api'),
  ('Outsmart the Amateur', 'School Daze', 'af2275ea-1085-4145-aa6b-36924d53d88a', 'https://scryfall.com/card/om1/37/school-daze?utm_source=api'),
  ('Ozor, Chronicler of Collapse', 'Doc Ock, Sinister Scientist', 'dbaa70e6-26de-4ce9-9543-e652cbe387c1', 'https://scryfall.com/card/om1/38/doc-ock-sinister-scientist?utm_source=api'),
  ('Panic on Amity Island', 'Descent into Avernus', '1313da2f-92bb-4862-9153-373972cc1520', 'https://scryfall.com/card/sld/2176/descent-into-avernus?utm_source=api'),
  ('Panther Idol', 'Mind''s Eye', '63fd2a57-7a47-4e07-947c-f4e9da7ee538', 'https://scryfall.com/card/msc/447/minds-eye?utm_source=api'),
  ('Panthor, Savage Cat', 'The Gitrog, Ravenous Ride', '7739311a-682b-48a6-8db2-c07f44141751', 'https://scryfall.com/card/sld/2791/the-gitrog-ravenous-ride?utm_source=api'),
  ('Paradise Chocobo', 'Birds of Paradise', 'd3a0b660-358c-41bd-9cd2-41fbf3491b1a', 'https://scryfall.com/card/fic/483/birds-of-paradise?utm_source=api'),
  ('Pastor da Selva', 'Ancient Greenwarden', '3bcf090c-e890-4a9f-a8aa-6079e4ec9947', 'https://scryfall.com/card/sld/2059/ancient-greenwarden?utm_source=api'),
  ('Patchwork Chucky', 'Stuffy Doll', '499dceab-1890-49c8-b35d-b059a1dc950f', 'https://scryfall.com/card/sld/880/stuffy-doll?utm_source=api'),
  ('Paths of the Dead', 'Cavern of Souls', '89ca686a-7c72-4d8f-9290-e89635624a83', 'https://scryfall.com/card/ltc/392/cavern-of-souls?utm_source=api'),
  ('Patrick Star', 'Barktooth Warbeard', '4a221518-c850-4e8a-a697-765c0a0e76e7', 'https://scryfall.com/card/sld/1931/barktooth-warbeard?utm_source=api'),
  ('Patriotic Shield', 'Sword of Fire and Ice', '2ccdc60a-49a9-44b9-a7af-0ebf18b26785', 'https://scryfall.com/card/mar/100/sword-of-fire-and-ice?utm_source=api'),
  ('Pelican Town', 'Homeward Path', 'cb8ec2e4-8223-4172-8f2c-37c918a573fa', 'https://scryfall.com/card/sld/2811/homeward-path?utm_source=api'),
  ('Perfect Defense', 'Defense of the Heart', 'e7e1b166-9267-426d-897d-24903327b48d', 'https://scryfall.com/card/sld/1039/defense-of-the-heart?utm_source=api'),
  ('Perfected Pastry', 'Bagel and Schmear', '1389c9fa-fec2-4212-a7aa-6dfb318dc202', 'https://scryfall.com/card/om1/170/bagel-and-schmear?utm_source=api'),
  ('Perilous Lunge', 'Kapow!', 'd6eabbff-cc0c-4000-8feb-4826e1b6bc66', 'https://scryfall.com/card/om1/111/kapow!?utm_source=api'),
  ('Phantasmal Vision', 'Mysterio''s Phantasm', '99419378-8a23-44f3-aebe-e62d6e20e877', 'https://scryfall.com/card/om1/39/mysterios-phantasm?utm_source=api'),
  ('Phenomena Recorder', 'Peter Parker''s Camera', '10777360-c046-43e3-ab44-9d0b926fbbf8', 'https://scryfall.com/card/om1/171/peter-parkers-camera?utm_source=api'),
  ('Pierre''s Truce', 'Dawn''s Truce', '37c06f89-db36-4937-9404-2b07cd22e1a6', 'https://scryfall.com/card/sld/2803/dawns-truce?utm_source=api'),
  ('Pigsy of the Eight Precepts', 'Ilharg, the Raze-Boar', '8d571129-9030-47e0-9624-a49fb63e5a1b', 'https://scryfall.com/card/sld/2402/ilharg-the-raze-boar?utm_source=api'),
  ('Piko Piko Hammer', 'Hammer of Nazahn', 'e3955573-3db5-490e-903e-65e0172a9202', 'https://scryfall.com/card/sld/2098/hammer-of-nazahn?utm_source=api'),
  ('Pinnacle Research Team', 'Oscorp Research Team', '4d2e233c-0173-417f-82a0-1e692a400ae1', 'https://scryfall.com/card/om1/40/oscorp-research-team?utm_source=api'),
  ('Plankton, Tiny Tyrant', 'Skrelv, Defector Mite', '20053847-6623-493c-8cdb-a69cda3b1577', 'https://scryfall.com/card/sld/1926/skrelv-defector-mite?utm_source=api'),
  ('Play Pals Factory', 'Genesis Chamber', '150ab025-5cc3-4468-a724-bbba8838445d', 'https://scryfall.com/card/sld/1811/genesis-chamber?utm_source=api'),
  ('Porom''s Silence Magic', 'Silence', '8aed54cb-d1bb-45ad-adbe-38e55d84ff31', 'https://scryfall.com/card/sld/7003/silence?utm_source=api'),
  ('Post the Enchanter', 'Zur the Enchanter', 'd7950018-d744-48a8-81aa-0d8384703f48', 'https://scryfall.com/card/sld/726/zur-the-enchanter?utm_source=api'),
  ('Post''s Citadel', 'Bolas''s Citadel', '2bd111bb-ce02-414c-b5b7-e0e037d8d96b', 'https://scryfall.com/card/sld/1187/bolass-citadel?utm_source=api'),
  ('Post''s Sigil', 'Leshrac''s Sigil', '98388eba-31ab-4302-be9e-ea67ea2b8c1a', 'https://scryfall.com/card/sld/1188/leshracs-sigil?utm_source=api'),
  ('Post, Son of Rich', 'K''rrik, Son of Yawgmoth', 'cbe3a4e7-5dbe-4f58-8ee6-a1762b65acfd', 'https://scryfall.com/card/sld/1186/krrik-son-of-yawgmoth?utm_source=api'),
  ('Power Sneakers', 'Lightning Greaves', 'ca204b66-8d0c-431a-8d34-282f7c2d17da', 'https://scryfall.com/card/sld/2099/lightning-greaves?utm_source=api'),
  ('Prime Mirelurk Queen', 'Hullbreaker Horror', 'd4a84e78-d9b9-4c67-8a4b-4329e65f0f15', 'https://scryfall.com/card/pip/872/hullbreaker-horror?utm_source=api'),
  ('Primogenesis', 'Feed the Swarm', '5825997b-10d7-4a36-972c-a80ddd90b8ed', 'https://scryfall.com/card/sld/7001/feed-the-swarm?utm_source=api'),
  ('Princess Sarah', 'Azusa, Lost but Seeking', '6c2c8bf3-9bf8-4a86-89d3-3bb36260dc51', 'https://scryfall.com/card/fca/15/azusa-lost-but-seeking?utm_source=api'),
  ('Principled Referee', 'Daily Bugle Reporters', '2e677ded-7af3-4af0-81df-b70d6ee616ec', 'https://scryfall.com/card/om1/16/daily-bugle-reporters?utm_source=api'),
  ('Prophetic Beginning', 'Preordain', 'ac641490-ca14-48d7-8cc4-b69ce984befa', 'https://scryfall.com/card/sch/39/preordain?utm_source=api'),
  ('Qoneus, Horizon Splicer', 'The Spot, Living Portal', 'a5dfa7ad-9637-4da8-9ed2-0ac863617d9a', 'https://scryfall.com/card/om1/150/the-spot-living-portal?utm_source=api'),
  ('Quincey Harker', 'Reclusive Taxidermist', '7a0168c5-e258-4c50-96aa-95deb2198e6f', 'https://scryfall.com/card/vow/340/reclusive-taxidermist?utm_source=api'),
  ('Quint''s Insight', 'Shadow of the Goblin', 'f343b6f9-41c3-419b-a57c-a7b08603ef5c', 'https://scryfall.com/card/om1/90/shadow-of-the-goblin?utm_source=api'),
  ('Quite a Merry Gathering', 'Tocasia''s Welcome', '25c983e0-a8c9-4784-91a4-8fe04c6df882', 'https://scryfall.com/card/sld/2553/tocasias-welcome?utm_source=api'),
  ('Raise Repulsor Shields', 'Raise the Palisade', 'f55a3781-fe33-4301-9bb5-6a54b9c13c4f', 'https://scryfall.com/card/msc/340/raise-the-palisade?utm_source=api'),
  ('Rally the Evil Warriors', 'Breach the Multiverse', 'ebbd5b9c-07ff-4b42-81c2-ba09539f3a42', 'https://scryfall.com/card/sld/2777/breach-the-multiverse?utm_source=api'),
  ('Raph''s Jitte', 'Umezawa''s Jitte', '1da10d5c-36a8-473f-a5d4-782ad61d8057', 'https://scryfall.com/card/pza/19/umezawas-jitte?utm_source=api'),
  ('Rathalos, King of the Skies', 'Drakuseth, Maw of Flames', '060deaff-44d6-4f03-9568-bcb7add80255', 'https://scryfall.com/card/sld/2237/drakuseth-maw-of-flames?utm_source=api'),
  ('Re-Roll', 'Rewind', 'bb27bfdf-fe8d-45bd-ad62-8118dce06eda', 'https://scryfall.com/card/sld/1036/rewind?utm_source=api'),
  ('Reality Fulcrum', 'Interdimensional Web Watch', '456dbec4-1b0e-48c4-abae-5c8205651872', 'https://scryfall.com/card/om1/172/interdimensional-web-watch?utm_source=api'),
  ('Recyclops, Eco-friendly', 'Garruk Relentless', '7cec9021-6f25-4fd8-b40e-adf4ffd3a7b8', 'https://scryfall.com/card/sld/2169/garruk-relentless-garruk-the-veil-cursed?utm_source=api'),
  ('Redhorn Pass', 'Mouth of Ronom', '7c05d239-39fc-4d34-a853-e3d591f4a235', 'https://scryfall.com/card/ltc/400z/mouth-of-ronom?utm_source=api'),
  ('Regalla''s Wrath', 'Tarrian''s Soulcleaver', '2ffb38ec-5852-4e91-85a5-cfccd1f23556', 'https://scryfall.com/card/sld/2224/tarrians-soulcleaver?utm_source=api'),
  ('Remarkable Readings', 'Friendly Neighborhood', '10fe402e-8d6f-4058-9f42-86f229055359', 'https://scryfall.com/card/om1/17/friendly-neighborhood?utm_source=api'),
  ('Remorseless Coup', 'The Spot''s Portal', '3ceac6ce-acde-42ab-b79d-ff153074d2d8', 'https://scryfall.com/card/om1/65/the-spots-portal?utm_source=api'),
  ('Renfield, Delusional Minion', 'Eruth, Tormented Prophet', 'a0380b63-58ef-4545-beec-6ad307bbc21b', 'https://scryfall.com/card/vow/342/eruth-tormented-prophet?utm_source=api'),
  ('Restless Razorkin', 'Superior Foes of Spider-Man', 'a6a7af21-e52c-4f7f-a57f-bd365d075966', 'https://scryfall.com/card/om1/91/superior-foes-of-spider-man?utm_source=api'),
  ('Rhilex the Accursed', 'Agent Venom', '14c356aa-178d-4c14-a88e-fbe92ee6d89f', 'https://scryfall.com/card/om1/66/agent-venom?utm_source=api'),
  ('Rick, Steadfast Leader', 'Greymond, Avacyn''s Stalwart', '739a5220-50cd-4148-be58-1bbdeef2954e', 'https://scryfall.com/card/sld/143/greymond-avacyns-stalwart?utm_source=api'),
  ('Ring of Barahir', 'Sword of the Animist', 'd79cbc61-6c15-48ea-bbba-3cffb819ccba', 'https://scryfall.com/card/ltc/385z/sword-of-the-animist?utm_source=api'),
  ('Rishei, Getaway Accomplice', 'Vulture, Scheming Scavenger', '0409765a-bbb4-465e-99b3-3687bffc3cf9', 'https://scryfall.com/card/om1/152/vulture-scheming-scavenger?utm_source=api'),
  ('Rizna, the Spider-Crowned', 'Spinneret and Spiderling', 'daca1d5e-349d-4e8a-abc7-427dab43fb0c', 'https://scryfall.com/card/om1/92/spinneret-and-spiderling?utm_source=api'),
  ('Rodan, Titan of Winged Fury', 'Vadrok, Apex of Thunder', '775c41fa-2316-43c9-af34-ac9c9b0db7e2', 'https://scryfall.com/card/iko/383/vadrok-apex-of-thunder?utm_source=api'),
  ('Rodents of Unusual Size', 'Pack Rat', '5632c2df-71e6-41b7-b8f5-c683812cc0e2', 'https://scryfall.com/card/sld/1448/pack-rat?utm_source=api'),
  ('Ronin''s Arsenal', 'Conqueror''s Flail', '9aace0d3-89e6-4254-b96f-ee3a878f2f91', 'https://scryfall.com/card/pza/15/conquerors-flail?utm_source=api'),
  ('Round Two', 'Seize the Day', '2a6abd59-e448-46f1-9af8-bb9040645971', 'https://scryfall.com/card/sld/480/seize-the-day?utm_source=api'),
  ('Rouse the Swarm', 'Wall Crawl', '4a09536e-dfc1-4b15-adc1-07ef866ebda0', 'https://scryfall.com/card/om1/112/wall-crawl?utm_source=api'),
  ('Royal Serpent', 'Atsushi, the Blazing Sky', '535f405d-94df-4f45-aedc-b331103720b7', 'https://scryfall.com/card/sld/2814/atsushi-the-blazing-sky?utm_source=api'),
  ('Ruzic, Booed but Victorious', 'Ultimate Green Goblin', 'b5b43d01-fce6-4a00-9c19-7a7e2a09d833', 'https://scryfall.com/card/om1/153/ultimate-green-goblin?utm_source=api'),
  ('Ruzka, Terror of Point Lookout', 'Ayula, Queen Among Bears', 'a79d2fc8-467f-464d-9e73-2dae4b059628', 'https://scryfall.com/card/pip/876/ayula-queen-among-bears?utm_source=api'),
  ('Ryu, World Warrior', 'Vikya, Scorching Stalwart', 'ad43ccce-3052-4817-8c46-f5c23cb49300', 'https://scryfall.com/card/sld/429/vikya-scorching-stalwart?utm_source=api'),
  ('S.H.I.E.L.D. Spy Satellite', 'Fellwar Stone', '95560508-7ac9-4be9-8a3f-3c7d5b52807b', 'https://scryfall.com/card/msc/285/fellwar-stone?utm_source=api'),
  ('Sadistic String-Puller', 'Spider-Islanders', '2d1a15dc-3123-4425-b036-a3b5a83fcdf8', 'https://scryfall.com/card/om1/94/spider-islanders?utm_source=api'),
  ('Sandy Cheeks, Martial Astronaut', 'Toski, Bearer of Secrets', 'a8e707ec-ce77-4bc5-8c76-5ea3e81e8c7f', 'https://scryfall.com/card/sld/1930/toski-bearer-of-secrets?utm_source=api'),
  ('Sandy, Awakened to Purity', 'Kazuul, Tyrant of the Cliffs', 'f8bf3d91-cb50-48ce-88c6-cdcb37b64b57', 'https://scryfall.com/card/sld/2403/kazuul-tyrant-of-the-cliffs?utm_source=api'),
  ('Sarn of the Silken Throne', 'Spider-UK', 'ebf8d006-2997-431b-b4cb-9692741b45ca', 'https://scryfall.com/card/om1/18/spider-uk?utm_source=api'),
  ('Scions of the Ur-Spider', 'Cosmic Spider-Man', '0334a2f8-a74a-44c9-ba64-d9b7fabe160c', 'https://scryfall.com/card/om1/154/cosmic-spider-man?utm_source=api'),
  ('Scorvus Ames, Crimelord', 'Scorpion, Seething Striker', 'c357230a-afde-4c2a-b390-9f6928599236', 'https://scryfall.com/card/om1/68/scorpion-seething-striker?utm_source=api'),
  ('Scrounging Deathclaw', 'Tarmogoyf', '45900b2f-f6a9-4c42-9642-008f3c1cf6dd', 'https://scryfall.com/card/pip/877/tarmogoyf?utm_source=api'),
  ('Scuttling Spidercoach', 'Spider-Mobile', '3c322d99-2bc4-4618-aeb3-5583fce54f1b', 'https://scryfall.com/card/om1/173/spider-mobile?utm_source=api'),
  ('Search for the Frozen Esper', 'Nature''s Claim', '6d4e558e-9109-4918-a082-fdcbaffd516b', 'https://scryfall.com/card/fca/47/natures-claim?utm_source=api'),
  ('Search the Count''s Castle', 'Thirst for Discovery', '1e05e6ef-14af-451d-9d54-e75b1f8871ab', 'https://scryfall.com/card/vow/333/thirst-for-discovery?utm_source=api'),
  ('Second Breakfast 9:00 AM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2546/food?utm_source=api'),
  ('Selesnya Archivist', 'Damage Control Crew', 'c0f9e604-a8bf-4c7d-8480-487e8076e1d8', 'https://scryfall.com/card/om1/115/damage-control-crew?utm_source=api'),
  ('Sephiroth, the Savior', 'Atraxa, Grand Unifier', 'abbcb153-0763-44c6-964f-b4ff0eb64257', 'https://scryfall.com/card/fca/49/atraxa-grand-unifier?utm_source=api'),
  ('Seymour Guado', 'Kinnan, Bonder Prodigy', '8d11aa49-d4cd-48b1-aa0f-8548fa733416', 'https://scryfall.com/card/fca/55/kinnan-bonder-prodigy?utm_source=api'),
  ('Shadowbringers', 'Dovin''s Veto', '1b388371-f9ef-45b4-82a3-ca20a8cd7807', 'https://scryfall.com/card/fca/51/dovins-veto?utm_source=api'),
  ('Shantotto''s Coercion', 'Diabolic Intent', '038519b9-bca8-4b27-b5ac-2409595469d0', 'https://scryfall.com/card/fca/34/diabolic-intent?utm_source=api'),
  ('Shards of Narsil', 'Thorn of Amethyst', '0c6c5336-9233-4ab1-9d55-79f20be7ea57', 'https://scryfall.com/card/ltc/386z/thorn-of-amethyst?utm_source=api'),
  ('She-Ra, Princess of Power', 'Sisay, Weatherlight Captain', 'fb777610-7562-4d9d-8497-62c562e6d7cb', 'https://scryfall.com/card/sld/2778/sisay-weatherlight-captain?utm_source=api'),
  ('Sheldon, the Commander', 'Ruhan of the Fomori', '82d109ea-3421-46eb-9bbf-f7f28b548ea6', 'https://scryfall.com/card/sld/1695/ruhan-of-the-fomori?utm_source=api'),
  ('Shelob, Whose Lair Is Death', 'Ishkanah, Grafwidow', '6f4861f4-1b3b-4dbc-b55b-196075d0a693', 'https://scryfall.com/card/ltc/516/ishkanah-grafwidow?utm_source=api'),
  ('Shield of War and Peace', 'Sword of War and Peace', 'b10ad415-0aae-4d70-82e6-a4055a40cbe4', 'https://scryfall.com/card/sld/1730/sword-of-war-and-peace?utm_source=api'),
  ('Shiva', 'Subtlety', '377179d5-ac83-4d34-b5b1-f3d8caa60f79', 'https://scryfall.com/card/sld/7005/subtlety?utm_source=api'),
  ('Shovel of Decapitation', 'Colossus Hammer', '8ec03b88-8d3a-4a32-8b7c-7da59b0c03d0', 'https://scryfall.com/card/sld/736/colossus-hammer?utm_source=api'),
  ('Shredder, Criminal Mastermind', 'Higure, the Still Wind', '01197456-62f1-4bc0-9f2f-127f97f9b05d', 'https://scryfall.com/card/sld/2368/higure-the-still-wind?utm_source=api'),
  ('Shrinking Storm', 'Wrath of God', '34515b16-c9a4-4f98-8c77-416a7a523407', 'https://scryfall.com/card/sld/441/wrath-of-god?utm_source=api'),
  ('Shu Jing Meteorite', 'Fellwar Stone', '95560508-7ac9-4be9-8a3f-3c7d5b52807b', 'https://scryfall.com/card/sld/7062/fellwar-stone?utm_source=api'),
  ('Simon, Wild Magic Sorcerer', 'Mathise, Surge Channeler', '61be7df8-cc78-4822-9e70-f226a8a96c9d', 'https://scryfall.com/card/sld/1238/mathise-surge-channeler?utm_source=api'),
  ('Sir Bedivere''s Scales', 'Ashnod''s Altar', '4d18bcba-a346-445e-a182-6cc30b7e066d', 'https://scryfall.com/card/sld/1679/ashnods-altar?utm_source=api'),
  ('Sisters of the Undead', 'Olivia, Crimson Bride', '8922a91e-3d15-4351-8d77-e0d6bc4de82e', 'https://scryfall.com/card/vow/343/olivia-crimson-bride?utm_source=api'),
  ('Skeletor''s Villainous Glee', 'Tasha''s Hideous Laughter', 'e352f5b9-6406-4914-bc79-f24608be6bc9', 'https://scryfall.com/card/sld/2774/tashas-hideous-laughter?utm_source=api'),
  ('Skeletor, Lord of Destruction', 'Tinybones, the Pickpocket', '7bc4c7e2-6758-4a85-84e7-03ab93981106', 'https://scryfall.com/card/sld/2773/tinybones-the-pickpocket?utm_source=api'),
  ('Skittering Kitten', 'Masked Meower', 'a0037ff8-64db-45dd-bba1-db5c49095083', 'https://scryfall.com/card/om1/96/masked-meower?utm_source=api'),
  ('Skv''x the Augmenter', 'Symbiote Spider-Man', 'bc681ecf-2a52-4782-9a47-90f5a9f435d8', 'https://scryfall.com/card/om1/155/symbiote-spider-man?utm_source=api'),
  ('Skybreaker, Sword of Bashenga', 'Sword of the Animist', 'd79cbc61-6c15-48ea-bbba-3cffb819ccba', 'https://scryfall.com/card/msc/452/sword-of-the-animist?utm_source=api'),
  ('Slash Clone', 'Steelbane Hydra', 'e38e3723-05f5-4a51-8364-1cda19f9cc49', 'https://scryfall.com/card/tmc/52/steelbane-hydra?utm_source=api'),
  ('Slash, Evil Turtle from Dimension X', 'Pirated Copy', '09ea5508-78fd-4bbc-8395-38ec13202d9a', 'https://scryfall.com/card/sld/2363/pirated-copy?utm_source=api'),
  ('Slimed', 'Trickbind', '0c2abd2a-ca98-45d2-8dd1-984d2c0c266a', 'https://scryfall.com/card/sld/1774/trickbind?utm_source=api'),
  ('Slimer and Stay Puft', 'Yargle and Multani', '980e1721-3717-4425-95a4-938dbf2ac661', 'https://scryfall.com/card/sld/872/yargle-and-multani?utm_source=api'),
  ('Slimer''s Feast', 'Windfall', '08becc07-28bc-4a2f-a6b0-28a2998d2f50', 'https://scryfall.com/card/sld/1775/windfall?utm_source=api'),
  ('Slimer, Voracious Apparition', 'The Mimeoplasm', '55123455-d435-46d4-b0cd-0c1614343be2', 'https://scryfall.com/card/sld/1773/the-mimeoplasm?utm_source=api'),
  ('Snatch Back', 'Whoosh!', '855353e2-b686-482a-b987-c6ae456f088c', 'https://scryfall.com/card/om1/43/whoosh!?utm_source=api'),
  ('Snowman Starfield', 'Starfield of Nyx', '922d603e-6623-4455-b91f-fad76f94045a', 'https://scryfall.com/card/sld/2822/starfield-of-nyx?utm_source=api'),
  ('Song of the Barbarous Beast', 'Village Rites', '365548fb-5acc-4a8a-b20b-26d28b7d029f', 'https://scryfall.com/card/sld/2248/village-rites?utm_source=api'),
  ('Sorry, Jack . . . Chucky''s Back', 'Phyrexian Reclamation', '647ca69e-cc01-4b2b-b376-bee2a98331e8', 'https://scryfall.com/card/sld/1808/phyrexian-reclamation?utm_source=api'),
  ('Spacegodzilla, Death Corona', 'Void Beckoner', '7185e345-d8a1-4dd3-a071-f90f265634b4', 'https://scryfall.com/card/iko/373/void-beckoner?utm_source=api'),
  ('Specimen 73', 'Hornet Queen', '3b1f8108-6911-49e9-8f78-f950bb58cb6c', 'https://scryfall.com/card/pip/878/hornet-queen?utm_source=api'),
  ('Spectral Restitching', 'Hide on the Ceiling', '376fa374-ead1-4728-ab8b-aca230b72031', 'https://scryfall.com/card/om1/44/hide-on-the-ceiling?utm_source=api'),
  ('Spider-Gwen, Web-Warrior', 'Najeela, the Blade-Blossom', '09619943-6aec-4080-ace5-a0c6ebb23f1c', 'https://scryfall.com/card/mar/24/najeela-the-blade-blossom?utm_source=api'),
  ('Spinosaurus', 'Regisaur Alpha', '0673f4e0-66ff-458c-b4ba-eb067e560cce', 'https://scryfall.com/card/sld/1393%E2%98%85/regisaur-alpha?utm_source=api'),
  ('Spira''s Punishment', 'Day of Judgment', 'd057289d-5e28-43d5-8ff3-4a1bc723477d', 'https://scryfall.com/card/sld/1858/day-of-judgment?utm_source=api'),
  ('Splinter of the Shadows', 'Ashcoat of the Shadow Swarm', '9cc69ea5-42a2-4306-ac6d-cff5adb20bcb', 'https://scryfall.com/card/pza/6/ashcoat-of-the-shadow-swarm?utm_source=api'),
  ('Splinter, Vengeful Sensei', 'Ink-Eyes, Servant of Oni', '5d520476-740a-4005-801e-472b24fa6497', 'https://scryfall.com/card/sld/2374/ink-eyes-servant-of-oni?utm_source=api'),
  ('SpongeBob SquarePants', 'Jodah, the Unifier', '490a8045-e160-4ccf-a05e-658ad2b7ac2d', 'https://scryfall.com/card/sld/1932/jodah-the-unifier?utm_source=api'),
  ('Squall Leonhart', 'Danitha Capashen, Paragon', '4b6377da-83e7-4519-9582-16a9c16b8faa', 'https://scryfall.com/card/fca/22/danitha-capashen-paragon?utm_source=api'),
  ('Squidward, Sarcastic Snob', 'Grazilaxx, Illithid Scholar', 'd22ff377-d282-4a28-9dce-96f25913dc96', 'https://scryfall.com/card/sld/1928/grazilaxx-illithid-scholar?utm_source=api'),
  ('Stampeding Brutes', 'Rampaging Baloths', '2d3e6549-6cc6-434f-a189-ba3b55e64c34', 'https://scryfall.com/card/sld/2370/rampaging-baloths?utm_source=api'),
  ('Stardrake', 'Scourge of the Throne', '06496a05-7f1a-402c-9594-304cd82bfefd', 'https://scryfall.com/card/sld/1033/scourge-of-the-throne?utm_source=api'),
  ('Stay with Me', 'Rhystic Study', '53236dd7-845a-444c-96d5-f41ed7325d8f', 'https://scryfall.com/card/fca/31/rhystic-study?utm_source=api'),
  ('Steelweb Surveyor', 'Spider-Bot', 'e4bb33b2-adde-4176-9274-7598b559aa6a', 'https://scryfall.com/card/om1/174/spider-bot?utm_source=api'),
  ('Stitcher''s Wings', 'Rocket-Powered Goblin Glider', '5db9121d-934a-44f1-b178-b389c6595af7', 'https://scryfall.com/card/om1/175/rocket-powered-goblin-glider?utm_source=api'),
  ('Storm''s Will', 'Jeska''s Will', '0fd114c4-092b-4e28-b0dc-ef529f3bc73e', 'https://scryfall.com/card/sld/1744/jeskas-will?utm_source=api'),
  ('Storms of Yamatai', 'Anger of the Gods', '3a7fe095-8278-4b1d-bec4-19b35bdcdd1b', 'https://scryfall.com/card/sld/1503/anger-of-the-gods?utm_source=api'),
  ('Suki of the Kyoshi Warriors', 'Captain Sisay', '2e7a9ea9-f76c-4c12-950f-c613fa16cfa8', 'https://scryfall.com/card/tle/47/captain-sisay?utm_source=api'),
  ('Summoner''s Rift', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/697/command-tower?utm_source=api'),
  ('Sunset Sarsaparilla Machine', 'Nuka-Cola Vending Machine', '6cfb03e5-aca6-4fe2-a3f1-93e1f0cbf9e1', 'https://scryfall.com/card/sld/2462/nuka-cola-vending-machine?utm_source=api'),
  ('Supper 8:00 PM', 'Food', 'a468338f-635e-4206-89d6-72d723071d45', 'https://scryfall.com/card/sld/2551/food?utm_source=api'),
  ('Supply Llama', 'Etherium Sculptor', '96b87445-6362-4a17-91b2-cbf203fd03fd', 'https://scryfall.com/card/sld/443/etherium-sculptor?utm_source=api'),
  ('Surris, Spidersilk Innovator', 'Peter Parker', 'f1b7488c-c675-42e9-818a-24a50347ec2c', 'https://scryfall.com/card/om1/21/peter-parker-amazing-spider-man?utm_source=api'),
  ('Swift Wind, Steed of She-Ra', 'Emiel the Blessed', 'b11c250c-f191-4c52-ba02-a9176f163447', 'https://scryfall.com/card/sld/2780/emiel-the-blessed?utm_source=api'),
  ('Sword of Power', 'Sword of War and Peace', 'b10ad415-0aae-4d70-82e6-a4055a40cbe4', 'https://scryfall.com/card/sld/2793/sword-of-war-and-peace?utm_source=api'),
  ('T''Challa''s Protection', 'Teferi''s Protection', '0d4ecdb1-ec90-497f-a7a4-1c68092b8757', 'https://scryfall.com/card/mar/51/teferis-protection?utm_source=api'),
  ('T-60 Power Armor', 'T-45 Power Armor', '370aced9-d8bc-4abe-b648-4c62b5aee5ba', 'https://scryfall.com/card/sld/2452/t-45-power-armor?utm_source=api'),
  ('Talk to the Paw', 'Orim''s Chant', '26d3a818-7faf-443a-a6bd-9773edaedf17', 'https://scryfall.com/card/sld/2669/orims-chant?utm_source=api'),
  ('Tarantusk, Unwisely Awoken', 'Spider-Ham, Peter Porker', '00b50215-e832-417f-9c80-2bc3050b6ebb', 'https://scryfall.com/card/om1/118/spider-ham-peter-porker?utm_source=api'),
  ('Tearle, Entropic Hunger', 'Morbius the Living Vampire', '1a947e4d-8a14-45f1-bb80-760a317b1ed0', 'https://scryfall.com/card/om1/156/morbius-the-living-vampire?utm_source=api'),
  ('Teela, Warrior Goddess', 'Samut, Voice of Dissent', 'b1eee275-5106-4c8d-a497-d7945ad81d74', 'https://scryfall.com/card/sld/2788/samut-voice-of-dissent?utm_source=api'),
  ('Temple Trap', 'Steel Wrecking Ball', '3a07e22c-71cd-4723-b07e-0ff02009a878', 'https://scryfall.com/card/om1/176/steel-wrecking-ball?utm_source=api'),
  ('Terra Branford', 'Urza, Lord High Artificer', 'e87906d2-db1a-4e19-b910-adb4eb339945', 'https://scryfall.com/card/fca/5/urza-lord-high-artificer?utm_source=api'),
  ('Tethex, Gift of Malice', 'Venom, Evil Unleashed', '6731d861-cc52-4a2e-8c33-154681fd50e4', 'https://scryfall.com/card/om1/70/venom-evil-unleashed?utm_source=api'),
  ('The Ball', 'Fellwar Stone', '95560508-7ac9-4be9-8a3f-3c7d5b52807b', 'https://scryfall.com/card/sld/1040/fellwar-stone?utm_source=api'),
  ('The Banyan Tree', 'The Great Henge', '78427103-9543-41fb-b6d4-72963fe87275', 'https://scryfall.com/card/tle/41/the-great-henge?utm_source=api'),
  ('The Black Beast of Aaargh', 'Marit Lage', '48e9147e-59f7-4693-83d7-7f514be871bc', 'https://scryfall.com/card/sld/1681/marit-lage?utm_source=api'),
  ('The Blades of Chaos Bond', 'Rite of Flame', '8a2e53f9-8100-488f-8504-b59e9bd1cc29', 'https://scryfall.com/card/sld/2209/rite-of-flame?utm_source=api'),
  ('The Boy in the Iceberg', 'Dark Depths', 'c9b82110-7dfd-4617-9399-9510be449043', 'https://scryfall.com/card/tle/56/dark-depths?utm_source=api'),
  ('The Bridge of Death', 'Door to Nothingness', 'b919cca5-88c0-4104-b54e-49644fbf78a5', 'https://scryfall.com/card/sld/1678/door-to-nothingness?utm_source=api'),
  ('The Cloudsea Djinn', 'Nyxbloom Ancient', '8b610f8f-c8dd-4eeb-bc6e-3bc706d5f63e', 'https://scryfall.com/card/fca/16/nyxbloom-ancient?utm_source=api'),
  ('The Clutter Cluster', 'Spiders-Man, Heroic Horde', 'd21d7557-9702-46c1-8277-42a3442084c2', 'https://scryfall.com/card/om1/101/spiders-man-heroic-horde?utm_source=api'),
  ('The Cube', 'Planar Bridge', '853c6cc0-ed2b-4d65-add1-2449ade8cf68', 'https://scryfall.com/card/sld/447/planar-bridge?utm_source=api'),
  ('The Dead Marshes', 'Urborg, Tomb of Yawgmoth', 'db6174d7-211d-4817-b8e4-8384594c83f9', 'https://scryfall.com/card/ltc/405z/urborg-tomb-of-yawgmoth?utm_source=api'),
  ('The Devil Strahd', 'Strefan, Maurer Progenitor', '3cc745d2-5021-43ff-ace8-35011011e62a', 'https://scryfall.com/card/sld/2501/strefan-maurer-progenitor?utm_source=api'),
  ('The Emperor, Hell Tyrant', 'Yawgmoth, Thran Physician', 'a1e232c0-dc38-47be-a5a0-f68bc1d86a29', 'https://scryfall.com/card/fca/11/yawgmoth-thran-physician?utm_source=api'),
  ('The Five Arrive', 'Genesis Ultimatum', '06f42f49-32f0-413b-8437-b8efa4d647c2', 'https://scryfall.com/card/msc/402/genesis-ultimatum?utm_source=api'),
  ('The Grass-Cutting Sword', 'Sunforger', 'd1421070-a3cc-4af3-bf91-0f97372f4161', 'https://scryfall.com/card/sld/2381/sunforger?utm_source=api'),
  ('The Grim Whisper', 'Bow of Nylea', '361b965f-2ce7-49f8-84e7-7325ea0c948d', 'https://scryfall.com/card/sld/1504/bow-of-nylea?utm_source=api'),
  ('The Hexcore', 'Thran Dynamo', 'a699c663-8131-4045-9265-a83e86609374', 'https://scryfall.com/card/sld/483/thran-dynamo?utm_source=api'),
  ('The House Grows Hungry', 'The Death of Gwen Stacy', '2624b5c5-ba59-4e20-8e66-e463268366e4', 'https://scryfall.com/card/om1/58/the-death-of-gwen-stacy?utm_source=api'),
  ('The Imperial City of Archades', 'Wall of Omens', '5f601f48-d24b-4883-9fde-b3f620e7c9ea', 'https://scryfall.com/card/fca/27/wall-of-omens?utm_source=api'),
  ('The Infernus', 'Molten Man, Inferno Incarnate', 'c6fcf3c1-0626-4d53-92c0-caa22fa61e9a', 'https://scryfall.com/card/om1/82/molten-man-inferno-incarnate?utm_source=api'),
  ('The Mechanist, Tactical Tinkerer', 'Lita, Mechanical Engineer', '715cb547-726f-4bc8-ad46-297d4dccb881', 'https://scryfall.com/card/tle/4/lita-mechanical-engineer?utm_source=api'),
  ('The Monstrous Serpent', 'Koma, Cosmos Serpent', '6ba0656f-e0d2-4735-9c66-3a00afa9fc23', 'https://scryfall.com/card/tle/51/koma-cosmos-serpent?utm_source=api'),
  ('The Party Tree', 'The Great Henge', '78427103-9543-41fb-b6d4-72963fe87275', 'https://scryfall.com/card/ltc/378z/the-great-henge?utm_source=api'),
  ('The Platinum Chip', 'Caged Sun', '09b895ff-e729-48d1-bfc1-ea5fd7adda6a', 'https://scryfall.com/card/sld/2461/caged-sun?utm_source=api'),
  ('The Rage of Yian Garuga', 'Mizzium Mortars', '48ddba1e-2ad7-463f-9307-d2379a800e51', 'https://scryfall.com/card/sld/2249/mizzium-mortars?utm_source=api'),
  ('The Scouring Stormsoul', 'Sandman, Shifting Scoundrel', '8b205480-b1fb-490c-b1c9-cf5cc3c5acdb', 'https://scryfall.com/card/om1/113/sandman-shifting-scoundrel?utm_source=api'),
  ('The Shadow Lord', 'Gix, Yawgmoth Praetor', '928d977e-cff0-4e0e-83bb-16d73a754f35', 'https://scryfall.com/card/fca/35/gix-yawgmoth-praetor?utm_source=api'),
  ('The Sorceress, Heroic Guardian', 'Derevi, Empyrial Tactician', 'afa49a09-146f-4439-850e-dd1938c93cef', 'https://scryfall.com/card/sld/2787/derevi-empyrial-tactician?utm_source=api'),
  ('The Spire', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/677/command-tower?utm_source=api'),
  ('The Strahl', 'Smuggler''s Copter', '49136bdc-bc50-49a2-999a-1ef9c16ea130', 'https://scryfall.com/card/fca/62/smugglers-copter?utm_source=api'),
  ('The Terminus of Return', 'The Soul Stone', '92cfba68-12f6-4f97-9187-0f6a39656a0f', 'https://scryfall.com/card/om1/69/the-soul-stone?utm_source=api'),
  ('The Three Weird Sisters', 'Henrika Domnathi', '0c0845c3-f4b5-444e-8f42-da0c7dbf2841', 'https://scryfall.com/card/vow/335/henrika-domnathi-henrika-infernal-seer?utm_source=api'),
  ('The Watcher on the Road', 'Mysterio, Master of Illusion', '40f664d8-4c73-44aa-8fb1-d38771a42520', 'https://scryfall.com/card/om1/48/mysterio-master-of-illusion?utm_source=api'),
  ('The Watcher''s Warning', 'Mind''s Dilation', 'd4b5e09b-9ca2-4b51-a4f8-080741810df8', 'https://scryfall.com/card/msc/344/minds-dilation?utm_source=api'),
  ('The Welcoming Committee', 'Kynaios and Tiro of Meletis', '53ee4254-fef7-49ec-aafc-0320987764e6', 'https://scryfall.com/card/sld/2806/kynaios-and-tiro-of-meletis?utm_source=api'),
  ('Three Rings for the Elven-Kings', 'Rings of Brighthearth', 'bbf9494c-c4bb-4d36-98fe-8387846b342e', 'https://scryfall.com/card/ltc/382z/rings-of-brighthearth?utm_source=api'),
  ('Through the Omenpath', 'Web of Life and Destiny', '33d556c5-1bb4-49bb-88c2-627311eb8c9b', 'https://scryfall.com/card/om1/120/web-of-life-and-destiny?utm_source=api'),
  ('Throw Team-Mate', 'Fling', '24227761-b50e-4b9e-93a2-e82d053b3e3d', 'https://scryfall.com/card/sld/1038/fling?utm_source=api'),
  ('Thrum of the Vestige', 'Lightning Bolt', '4457ed35-7c10-48c8-9776-456485fdf070', 'https://scryfall.com/card/fca/40/lightning-bolt?utm_source=api'),
  ('Thunderjaw', 'Meteor Golem', 'd9f11aa1-9219-42a8-85a9-a8f204160706', 'https://scryfall.com/card/sld/2225/meteor-golem?utm_source=api'),
  ('Théoden, Strength Restored', 'Kenrith, the Returned King', 'd209b948-9afb-4fd1-a961-72c87282878c', 'https://scryfall.com/card/ltc/515/kenrith-the-returned-king?utm_source=api'),
  ('Tidus''s Brotherhood Sword', 'Sword of Truth and Justice', '7a8baaf9-e21f-41a0-9f15-80764f6e5e68', 'https://scryfall.com/card/sld/1867/sword-of-truth-and-justice?utm_source=api'),
  ('Tidus, Zanarkand Fayth', 'Thrasios, Triton Hero', '3d867016-2601-4a37-a73d-308898d3bd37', 'https://scryfall.com/card/fca/58/thrasios-triton-hero?utm_source=api'),
  ('Tiffany, Bride of Chucky', 'Varragoth, Bloodsky Sire', '68b41a04-8cb0-4edf-b488-a219494453ae', 'https://scryfall.com/card/sld/1809/varragoth-bloodsky-sire?utm_source=api'),
  ('Tim the Enchanter', 'Prodigal Sorcerer', '5e961d15-5972-4e4b-9385-1cd7cd7c6bbe', 'https://scryfall.com/card/sld/1672/prodigal-sorcerer?utm_source=api'),
  ('To the Crystal Tower', 'Cryptic Command', 'a3e51a35-09df-4189-b131-08a21e6a557d', 'https://scryfall.com/card/fca/29/cryptic-command?utm_source=api'),
  ('Torgal, Clive''s Companion', 'Yoshimaru, Ever Faithful', '963834c8-42df-4ee6-9b45-b9de88ce2eac', 'https://scryfall.com/card/pf25/5/yoshimaru-ever-faithful?utm_source=api'),
  ('Tornado, Sonic''s Biplane', 'Weatherlight', '73b3682f-396a-4ebe-aaac-6ce3ee36283a', 'https://scryfall.com/card/sld/2100/weatherlight?utm_source=api'),
  ('Total Containment Failure', 'Living End', '3939fbe0-3be4-41ef-828d-c93f2cb33b4f', 'https://scryfall.com/card/sld/1769/living-end?utm_source=api'),
  ('Totec''s Spear', 'Shadowspear', '8b27326f-e7b8-4a4d-b589-df459246d19a', 'https://scryfall.com/card/sld/1505/shadowspear?utm_source=api'),
  ('Touchdown!', 'Approach of the Second Sun', 'e4125377-34c0-4b54-bdf8-4e88f5d24565', 'https://scryfall.com/card/sld/1035/approach-of-the-second-sun?utm_source=api'),
  ('Tower of Cirith Ungol', 'Urborg', 'b6114962-035e-4e7f-9009-4739bf83a05a', 'https://scryfall.com/card/ltc/519/urborg?utm_source=api'),
  ('Tower of Rasmodius', 'Command Tower', '0895c9b7-ae7d-4bb3-af17-3b75deb50a25', 'https://scryfall.com/card/sld/2812/command-tower?utm_source=api'),
  ('Toxic Sheepsquatch', 'Gemrazer', '3dfb0c0a-b68f-43b9-8475-28d0192fc4ed', 'https://scryfall.com/card/pip/879/gemrazer?utm_source=api'),
  ('Trap Jaw, Wizard of Weapons', 'Tetsuo, Imperial Champion', '1111e042-0bce-4819-ab42-9912aed4d930', 'https://scryfall.com/card/sld/2789/tetsuo-imperial-champion?utm_source=api'),
  ('Treat Trolley', 'Hot Dog Cart', 'cf27f1f8-2d95-4a00-97f8-72a244837f08', 'https://scryfall.com/card/om1/177/hot-dog-cart?utm_source=api'),
  ('Treebeard, Eldest of Ents', 'Doran, the Siege Tower', 'a46d96d9-8e59-4777-8208-7730b9e33240', 'https://scryfall.com/card/ltc/517/doran-the-siege-tower?utm_source=api'),
  ('Triceratops', 'Wayward Swordtooth', '3875aef0-3102-4fbf-be90-e4139f7a2348', 'https://scryfall.com/card/sld/1392%E2%98%85/wayward-swordtooth?utm_source=api'),
  ('Tripitaka, Seeker from Tang', 'Dosan the Falling Leaf', '70e4025f-41de-4b47-a590-3c922dc1e209', 'https://scryfall.com/card/sld/2404/dosan-the-falling-leaf?utm_source=api'),
  ('Tyrannosaurus Rex', 'Etali, Primal Storm', '078def07-ae5d-4591-8db6-d156834aab97', 'https://scryfall.com/card/sld/1389%E2%98%85/etali-primal-storm?utm_source=api'),
  ('Uharis, the Stormspinner', 'Spider-Man 2099', '19845456-3d96-48a4-89fa-9b8e583774c9', 'https://scryfall.com/card/om1/157/spider-man-2099?utm_source=api'),
  ('Unseat the Usurper', 'Praetor''s Grasp', '6d56aeb1-0a50-46b6-abdb-cd6575a98dc3', 'https://scryfall.com/card/sld/1861/praetors-grasp?utm_source=api'),
  ('Unstable Harmonics', 'Rhystic Study', '53236dd7-845a-444c-96d5-f41ed7325d8f', 'https://scryfall.com/card/sld/478/rhystic-study?utm_source=api'),
  ('Vaan, Aspiring Sky Pirate', 'Captain Lannery Storm', '235bf0ba-658c-463f-b112-7478ba27bd7b', 'https://scryfall.com/card/fca/38/captain-lannery-storm?utm_source=api'),
  ('Valley Farmstead', 'Yavimaya, Cradle of Growth', '8dd5f5af-d2d8-4356-8617-8381081b930c', 'https://scryfall.com/card/sld/2813/yavimaya-cradle-of-growth?utm_source=api'),
  ('Valley of Gorgoroth', 'Wasteland', '09a70ae8-3859-4a09-901d-dce063fa3b5f', 'https://scryfall.com/card/ltc/406z/wasteland?utm_source=api'),
  ('Van Helsing''s Holy Ward', 'Circle of Confinement', 'd1cd7a93-4b83-4755-90bc-17cb64bfb131', 'https://scryfall.com/card/vow/329/circle-of-confinement?utm_source=api'),
  ('Vana''diel Adventurers', 'Laboratory Maniac', 'aa286dd5-aa19-446d-9003-684d81eb57ca', 'https://scryfall.com/card/fca/30/laboratory-maniac?utm_source=api'),
  ('Vault Boy, Cap Collector', 'Grand Arbiter Augustin IV', '1f8d4d5f-e82f-45f3-823e-1bb6b536eb18', 'https://scryfall.com/card/sld/1483%E2%98%85/grand-arbiter-augustin-iv?utm_source=api'),
  ('Vayne Carudas Solidor', 'Fynn, the Fangbearer', 'c0b1fba1-4338-4671-934b-098689ad2085', 'https://scryfall.com/card/fca/46/fynn-the-fangbearer?utm_source=api'),
  ('Vazin, Two-Faced Trickster', 'Chameleon, Master of Disguise', '1ce239f2-79ad-4a30-8e8f-f985045f78dc', 'https://scryfall.com/card/om1/46/chameleon-master-of-disguise?utm_source=api'),
  ('Velkhana, Silver Sovereign', 'Amareth, the Lustrous', '8cccc8d0-bdd8-4853-8330-6f6a57695d11', 'https://scryfall.com/card/sld/2254/amareth-the-lustrous?utm_source=api'),
  ('Velociraptor', 'Rampaging Ferocidon', '3e5ca524-8dd1-4f7f-a467-5210d768b8a1', 'https://scryfall.com/card/sld/1390%E2%98%85/rampaging-ferocidon?utm_source=api'),
  ('Venom, King in Black', 'Skithiryx, the Blight Dragon', 'daf6c421-e7f7-4fc6-967c-65f4ab96fcfd', 'https://scryfall.com/card/mar/22/skithiryx-the-blight-dragon?utm_source=api'),
  ('Verilax the Havenskin', 'Anti-Venom, Horrifying Healer', '3c7bafe9-80cd-48d0-bcae-e7910c9fb83b', 'https://scryfall.com/card/om1/22/anti-venom-horrifying-healer?utm_source=api'),
  ('Vexed Bots', 'Flying Octobot', '5ef8925c-5f43-49ca-83f0-e2ca8e655600', 'https://scryfall.com/card/om1/47/flying-octobot?utm_source=api'),
  ('Vibranium Dynamo', 'Thran Dynamo', 'a699c663-8131-4045-9265-a83e86609374', 'https://scryfall.com/card/msc/290/thran-dynamo?utm_source=api'),
  ('Viggo, Enforcer of Ig''s Crossing', 'Eddie Brock', 'fe01c96b-eb78-4477-bec2-944b2a28c778', 'https://scryfall.com/card/om1/71/eddie-brock-venom-lethal-protector?utm_source=api'),
  ('Vinewoven Chariot', 'Subway Train', '6d4472ad-3fbf-4a5d-94de-dfee04fda9c3', 'https://scryfall.com/card/om1/178/subway-train?utm_source=api'),
  ('Vivi''s Thunder Magic', 'Lightning Bolt', '4457ed35-7c10-48c8-9776-456485fdf070', 'https://scryfall.com/card/sld/1871/lightning-bolt?utm_source=api'),
  ('Vizzini, Criminal Mastermind', 'Baral, Chief of Compliance', 'baf80db7-2ca8-4bfc-b5b6-25ed51878dd7', 'https://scryfall.com/card/sld/1447/baral-chief-of-compliance?utm_source=api'),
  ('Volcano of Roku''s Island', 'Valakut, the Molten Pinnacle', '1bc44216-4e06-4f66-89b7-5c327004604e', 'https://scryfall.com/card/tle/61/valakut-the-molten-pinnacle?utm_source=api'),
  ('Wakandan Skyscraper', 'Karn''s Bastion', '9fb8cd81-403a-4988-8f1c-b8eccf8abd9c', 'https://scryfall.com/card/sld/1751/karns-bastion?utm_source=api'),
  ('Wakandan War Panther', 'Fleecemane Lion', 'e3c8cdf7-a26a-45eb-9498-99b618cfba99', 'https://scryfall.com/card/msc/423/fleecemane-lion?utm_source=api'),
  ('Wardens of Silverweb Summit', 'Spider-Gwen, Free Spirit', '2648559d-1d96-47d2-a769-cfa2cbca2be5', 'https://scryfall.com/card/om1/97/spider-gwen-free-spirit?utm_source=api'),
  ('Warrior of Light', 'Jodah, the Unifier', '490a8045-e160-4ccf-a05e-658ad2b7ac2d', 'https://scryfall.com/card/fca/17/jodah-the-unifier?utm_source=api'),
  ('We Want . . . A SHRUBBERY!', 'Three Visits', '1b882a0e-0ede-4d1a-bd1a-9b7cffbcde8e', 'https://scryfall.com/card/sld/1676/three-visits?utm_source=api'),
  ('Weathertop', 'Deserted Temple', '9f12bf9a-6e1a-4377-b4af-e8cabd3ee58a', 'https://scryfall.com/card/ltc/393z/deserted-temple?utm_source=api'),
  ('Wekhdu, Midnight Hunter', 'Swarm, Being of Bees', '10c8cf3b-2530-49e7-b38e-95cdaae8a6e7', 'https://scryfall.com/card/om1/73/swarm-being-of-bees?utm_source=api'),
  ('West Tek Tyrant', 'Grave Titan', 'f3abd4d1-a975-4e85-8684-aa0fce029670', 'https://scryfall.com/card/pip/874/grave-titan?utm_source=api'),
  ('Westley, Dread Pirate Roberts', 'Fynn, the Fangbearer', 'c0b1fba1-4338-4671-934b-098689ad2085', 'https://scryfall.com/card/sld/1449/fynn-the-fangbearer?utm_source=api'),
  ('White Tower of Ecthelion', 'Karakas', '59119143-c0fa-49dd-adf0-e2fd3029c48b', 'https://scryfall.com/card/ltc/397z/karakas?utm_source=api'),
  ('Widow-Making Infiltrator', 'Dauthi Voidwalker', 'f1c2dbe2-fbe0-4058-bdf1-91d1b1832786', 'https://scryfall.com/card/mar/63/dauthi-voidwalker?utm_source=api'),
  ('Wild Rose Rebellion', 'Counterspell', 'cc187110-1148-4090-bbb8-e205694a39f5', 'https://scryfall.com/card/fca/4/counterspell?utm_source=api'),
  ('Will the Wise', 'Wernog, Rider''s Chaplain', '6cd03270-54cc-43e1-9b86-70c76960c841', 'https://scryfall.com/card/sld/347/wernog-riders-chaplain?utm_source=api'),
  ('Withar, Cocoon Keeper', 'Mister Negative', 'c8da3262-826d-4ea8-bb22-06374bebefe5', 'https://scryfall.com/card/om1/158/mister-negative?utm_source=api'),
  ('Wonderweave Aerialist', 'Skyward Spider', 'd6ba76fa-441c-4a74-bfea-8ae2a2c9e391', 'https://scryfall.com/card/om1/159/skyward-spider?utm_source=api'),
  ('Wrench, Speedway Saboteur', 'Black Cat, Cunning Thief', 'f5cdb413-2b72-4dc6-b93d-2532ac2ae568', 'https://scryfall.com/card/om1/74/black-cat-cunning-thief?utm_source=api'),
  ('Xecau, Predation''s Shadow', 'Rhino, Barreling Brute', '9a6bf8a3-7640-4890-ac62-d5028f41978b', 'https://scryfall.com/card/om1/160/rhino-barreling-brute?utm_source=api'),
  ('Xenk, Paladin Unbroken', 'Rashel, Fist of Torm', 'c0c39f80-cf12-482e-a7c4-757db85125b0', 'https://scryfall.com/card/sld/1237/rashel-fist-of-torm?utm_source=api'),
  ('Ya viene el coco', 'Tibalt''s Trickery', '6623cb85-fb1e-4561-8b21-0977c25096c2', 'https://scryfall.com/card/sld/7027/tibalts-trickery?utm_source=api'),
  ('Yera and Oski, Weaver and Guide', 'Arachne, Psionic Weaver', '28d500ea-720f-4332-891e-404fb03acb5c', 'https://scryfall.com/card/om1/23/arachne-psionic-weaver?utm_source=api'),
  ('Yojimbo', 'Solitude', 'dcb9c2a7-ae54-4ddc-a567-640bf4bf4366', 'https://scryfall.com/card/sld/7004/solitude?utm_source=api'),
  ('You''re Gonna Need a Bigger Boat', 'Abrade', 'f9db72dc-9a5b-48a4-a86e-7464d9a2166a', 'https://scryfall.com/card/sld/2179/abrade?utm_source=api'),
  ('Yuffie Kisaragi', 'Yuriko, the Tiger''s Shadow', 'a7043fbd-1dfd-42cf-be4b-cc343d0949e5', 'https://scryfall.com/card/fca/60/yuriko-the-tigers-shadow?utm_source=api'),
  ('Yuna''s Holy Magic', 'Prismatic Ending', '2cb98ca9-d7bb-416b-a17e-ee5f8e4d78f2', 'https://scryfall.com/card/sld/1868/prismatic-ending?utm_source=api'),
  ('Yuna''s Sending Staff', 'Staff of the Storyteller', '0c4e2c90-c17b-42cc-b4d7-cf75970fbe90', 'https://scryfall.com/card/sld/1863/staff-of-the-storyteller?utm_source=api'),
  ('Zan, Tunnelweb Explorer', 'Spider-Man, Brooklyn Visionary', '2ca85872-9436-4515-af50-c13e59605627', 'https://scryfall.com/card/om1/122/spider-man-brooklyn-visionary?utm_source=api'),
  ('Zangief, the Red Cyclone', 'Maarika, Brutal Gladiator', 'a46f9f5c-775c-470d-8935-9556e1bbb23d', 'https://scryfall.com/card/sld/435/maarika-brutal-gladiator?utm_source=api'),
  ('Zidane Tribal', 'Ragavan, Nimble Pilferer', '37108cd4-bbab-4ce3-9ed6-f60e8422e703', 'https://scryfall.com/card/fca/43/ragavan-nimble-pilferer?utm_source=api'),
  ('Zinogre, Lord of Lightning', 'Sarulf, Realm Eater', '789964f5-79c5-4329-b68f-b15b0d54b0b2', 'https://scryfall.com/card/sld/2240/sarulf-realm-eater?utm_source=api'),
  ('Zora, Spider Fancier', 'Aunt May', 'bdb769b5-c861-4ec1-ad6b-e2a56ca05fd1', 'https://scryfall.com/card/om1/24/aunt-may?utm_source=api'),
  ('Zuko, Redeemed', 'Rhys the Redeemed', 'f7252190-ad24-4ba3-a644-2790dd1d680d', 'https://scryfall.com/card/tle/52/rhys-the-redeemed?utm_source=api'),
  ('Kavaero, Mind−Bitten', 'Superior Spider-Man', '636cc915-9d1b-4ffe-9e74-795b78663911', 'https://scryfall.com/card/om1/140/superior-spider-man?utm_source=api');

-- Display order comes from the saved project catalog, not Scryfall ordering.
CREATE TABLE public.commander_pair_display_order (
  pair_key text PRIMARY KEY,
  commander_names text[] NOT NULL CHECK (cardinality(commander_names)=2)
);
ALTER TABLE public.commander_pair_display_order ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON public.commander_pair_display_order FOR SELECT USING (true);
CREATE POLICY "Service role write access" ON public.commander_pair_display_order FOR ALL TO service_role USING (true) WITH CHECK (true);
GRANT SELECT ON public.commander_pair_display_order TO anon, authenticated;
GRANT ALL ON public.commander_pair_display_order TO service_role;
INSERT INTO public.commander_pair_display_order
SELECT key, ARRAY(SELECT jsonb_array_elements_text(value))
FROM jsonb_each($partner_order${
  "Abby, Merciless Soldier / Ellie, Brick Master": [
    "Abby, Merciless Soldier",
    "Ellie, Brick Master"
  ],
  "Abby, Merciless Soldier / Ellie, Vengeful Hunter": [
    "Abby, Merciless Soldier",
    "Ellie, Vengeful Hunter"
  ],
  "Abby, Merciless Soldier / Joel, Resolute Survivor": [
    "Abby, Merciless Soldier",
    "Joel, Resolute Survivor"
  ],
  "Abdel Adrian, Gorion's Ward / Acolyte of Bahamut": [
    "Abdel Adrian, Gorion's Ward",
    "Acolyte of Bahamut"
  ],
  "Abdel Adrian, Gorion's Ward / Agent of the Iron Throne": [
    "Abdel Adrian, Gorion's Ward",
    "Agent of the Iron Throne"
  ],
  "Abdel Adrian, Gorion's Ward / Agent of the Shadow Thieves": [
    "Abdel Adrian, Gorion's Ward",
    "Agent of the Shadow Thieves"
  ],
  "Abdel Adrian, Gorion's Ward / Candlekeep Sage": [
    "Abdel Adrian, Gorion's Ward",
    "Candlekeep Sage"
  ],
  "Abdel Adrian, Gorion's Ward / Clan Crafter": [
    "Abdel Adrian, Gorion's Ward",
    "Clan Crafter"
  ],
  "Abdel Adrian, Gorion's Ward / Cloakwood Hermit": [
    "Abdel Adrian, Gorion's Ward",
    "Cloakwood Hermit"
  ],
  "Abdel Adrian, Gorion's Ward / Criminal Past": [
    "Abdel Adrian, Gorion's Ward",
    "Criminal Past"
  ],
  "Abdel Adrian, Gorion's Ward / Cultist of the Absolute": [
    "Abdel Adrian, Gorion's Ward",
    "Cultist of the Absolute"
  ],
  "Abdel Adrian, Gorion's Ward / Dragon Cultist": [
    "Abdel Adrian, Gorion's Ward",
    "Dragon Cultist"
  ],
  "Abdel Adrian, Gorion's Ward / Dungeon Delver": [
    "Abdel Adrian, Gorion's Ward",
    "Dungeon Delver"
  ],
  "Abdel Adrian, Gorion's Ward / Faceless One": [
    "Abdel Adrian, Gorion's Ward",
    "Faceless One"
  ],
  "Abdel Adrian, Gorion's Ward / Far Traveler": [
    "Abdel Adrian, Gorion's Ward",
    "Far Traveler"
  ],
  "Abdel Adrian, Gorion's Ward / Feywild Visitor": [
    "Abdel Adrian, Gorion's Ward",
    "Feywild Visitor"
  ],
  "Abdel Adrian, Gorion's Ward / Flaming Fist": [
    "Abdel Adrian, Gorion's Ward",
    "Flaming Fist"
  ],
  "Abdel Adrian, Gorion's Ward / Folk Hero": [
    "Abdel Adrian, Gorion's Ward",
    "Folk Hero"
  ],
  "Abdel Adrian, Gorion's Ward / Guild Artisan": [
    "Abdel Adrian, Gorion's Ward",
    "Guild Artisan"
  ],
  "Abdel Adrian, Gorion's Ward / Hardy Outlander": [
    "Abdel Adrian, Gorion's Ward",
    "Hardy Outlander"
  ],
  "Abdel Adrian, Gorion's Ward / Haunted One": [
    "Abdel Adrian, Gorion's Ward",
    "Haunted One"
  ],
  "Abdel Adrian, Gorion's Ward / Inspiring Leader": [
    "Abdel Adrian, Gorion's Ward",
    "Inspiring Leader"
  ],
  "Abdel Adrian, Gorion's Ward / Master Chef": [
    "Abdel Adrian, Gorion's Ward",
    "Master Chef"
  ],
  "Abdel Adrian, Gorion's Ward / Noble Heritage": [
    "Abdel Adrian, Gorion's Ward",
    "Noble Heritage"
  ],
  "Abdel Adrian, Gorion's Ward / Passionate Archaeologist": [
    "Abdel Adrian, Gorion's Ward",
    "Passionate Archaeologist"
  ],
  "Abdel Adrian, Gorion's Ward / Popular Entertainer": [
    "Abdel Adrian, Gorion's Ward",
    "Popular Entertainer"
  ],
  "Abdel Adrian, Gorion's Ward / Raised by Giants": [
    "Abdel Adrian, Gorion's Ward",
    "Raised by Giants"
  ],
  "Abdel Adrian, Gorion's Ward / Scion of Halaster": [
    "Abdel Adrian, Gorion's Ward",
    "Scion of Halaster"
  ],
  "Abdel Adrian, Gorion's Ward / Shameless Charlatan": [
    "Abdel Adrian, Gorion's Ward",
    "Shameless Charlatan"
  ],
  "Abdel Adrian, Gorion's Ward / Street Urchin": [
    "Abdel Adrian, Gorion's Ward",
    "Street Urchin"
  ],
  "Abdel Adrian, Gorion's Ward / Sword Coast Sailor": [
    "Abdel Adrian, Gorion's Ward",
    "Sword Coast Sailor"
  ],
  "Abdel Adrian, Gorion's Ward / Tavern Brawler": [
    "Abdel Adrian, Gorion's Ward",
    "Tavern Brawler"
  ],
  "Abdel Adrian, Gorion's Ward / Veteran Soldier": [
    "Abdel Adrian, Gorion's Ward",
    "Veteran Soldier"
  ],
  "Ace, Fearless Rebel / The Eighth Doctor": [
    "Ace, Fearless Rebel",
    "The Eighth Doctor"
  ],
  "Ace, Fearless Rebel / The Eleventh Doctor": [
    "Ace, Fearless Rebel",
    "The Eleventh Doctor"
  ],
  "Ace, Fearless Rebel / The Fifteenth Doctor": [
    "Ace, Fearless Rebel",
    "The Fifteenth Doctor"
  ],
  "Ace, Fearless Rebel / The Fifth Doctor": [
    "Ace, Fearless Rebel",
    "The Fifth Doctor"
  ],
  "Ace, Fearless Rebel / The First Doctor": [
    "Ace, Fearless Rebel",
    "The First Doctor"
  ],
  "Ace, Fearless Rebel / The Fourteenth Doctor": [
    "Ace, Fearless Rebel",
    "The Fourteenth Doctor"
  ],
  "Ace, Fearless Rebel / The Fourth Doctor": [
    "Ace, Fearless Rebel",
    "The Fourth Doctor"
  ],
  "Ace, Fearless Rebel / The Fugitive Doctor": [
    "Ace, Fearless Rebel",
    "The Fugitive Doctor"
  ],
  "Ace, Fearless Rebel / The Ninth Doctor": [
    "Ace, Fearless Rebel",
    "The Ninth Doctor"
  ],
  "Ace, Fearless Rebel / The Second Doctor": [
    "Ace, Fearless Rebel",
    "The Second Doctor"
  ],
  "Ace, Fearless Rebel / The Seventh Doctor": [
    "Ace, Fearless Rebel",
    "The Seventh Doctor"
  ],
  "Ace, Fearless Rebel / The Sixth Doctor": [
    "Ace, Fearless Rebel",
    "The Sixth Doctor"
  ],
  "Ace, Fearless Rebel / The Tenth Doctor": [
    "Ace, Fearless Rebel",
    "The Tenth Doctor"
  ],
  "Ace, Fearless Rebel / The Third Doctor": [
    "Ace, Fearless Rebel",
    "The Third Doctor"
  ],
  "Ace, Fearless Rebel / The Thirteenth Doctor": [
    "Ace, Fearless Rebel",
    "The Thirteenth Doctor"
  ],
  "Ace, Fearless Rebel / The Twelfth Doctor": [
    "Ace, Fearless Rebel",
    "The Twelfth Doctor"
  ],
  "Ace, Fearless Rebel / The War Doctor": [
    "Ace, Fearless Rebel",
    "The War Doctor"
  ],
  "Acolyte of Bahamut / Alora, Merry Thief": [
    "Acolyte of Bahamut",
    "Alora, Merry Thief"
  ],
  "Acolyte of Bahamut / Amber Gristle O'Maul": [
    "Acolyte of Bahamut",
    "Amber Gristle O'Maul"
  ],
  "Acolyte of Bahamut / Baeloth Barrityl, Entertainer": [
    "Acolyte of Bahamut",
    "Baeloth Barrityl, Entertainer"
  ],
  "Acolyte of Bahamut / Burakos, Party Leader": [
    "Acolyte of Bahamut",
    "Burakos, Party Leader"
  ],
  "Acolyte of Bahamut / Durnan of the Yawning Portal": [
    "Acolyte of Bahamut",
    "Durnan of the Yawning Portal"
  ],
  "Acolyte of Bahamut / Ellyn Harbreeze, Busybody": [
    "Acolyte of Bahamut",
    "Ellyn Harbreeze, Busybody"
  ],
  "Acolyte of Bahamut / Erinis, Gloom Stalker": [
    "Acolyte of Bahamut",
    "Erinis, Gloom Stalker"
  ],
  "Acolyte of Bahamut / Faceless One": [
    "Acolyte of Bahamut",
    "Faceless One"
  ],
  "Acolyte of Bahamut / Gale, Waterdeep Prodigy": [
    "Acolyte of Bahamut",
    "Gale, Waterdeep Prodigy"
  ],
  "Acolyte of Bahamut / Ganax, Astral Hunter": [
    "Acolyte of Bahamut",
    "Ganax, Astral Hunter"
  ],
  "Acolyte of Bahamut / Gut, True Soul Zealot": [
    "Acolyte of Bahamut",
    "Gut, True Soul Zealot"
  ],
  "Acolyte of Bahamut / Halsin, Emerald Archdruid": [
    "Acolyte of Bahamut",
    "Halsin, Emerald Archdruid"
  ],
  "Acolyte of Bahamut / Imoen, Mystic Trickster": [
    "Acolyte of Bahamut",
    "Imoen, Mystic Trickster"
  ],
  "Acolyte of Bahamut / Jaheira, Friend of the Forest": [
    "Acolyte of Bahamut",
    "Jaheira, Friend of the Forest"
  ],
  "Acolyte of Bahamut / Karlach, Fury of Avernus": [
    "Acolyte of Bahamut",
    "Karlach, Fury of Avernus"
  ],
  "Acolyte of Bahamut / Lae'zel, Vlaakith's Champion": [
    "Acolyte of Bahamut",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Acolyte of Bahamut / Livaan, Cultist of Tiamat": [
    "Acolyte of Bahamut",
    "Livaan, Cultist of Tiamat"
  ],
  "Acolyte of Bahamut / Lulu, Loyal Hollyphant": [
    "Acolyte of Bahamut",
    "Lulu, Loyal Hollyphant"
  ],
  "Acolyte of Bahamut / Rasaad yn Bashir": [
    "Acolyte of Bahamut",
    "Rasaad yn Bashir"
  ],
  "Acolyte of Bahamut / Renari, Merchant of Marvels": [
    "Acolyte of Bahamut",
    "Renari, Merchant of Marvels"
  ],
  "Acolyte of Bahamut / Safana, Calimport Cutthroat": [
    "Acolyte of Bahamut",
    "Safana, Calimport Cutthroat"
  ],
  "Acolyte of Bahamut / Sarevok, Deathbringer": [
    "Acolyte of Bahamut",
    "Sarevok, Deathbringer"
  ],
  "Acolyte of Bahamut / Shadowheart, Dark Justiciar": [
    "Acolyte of Bahamut",
    "Shadowheart, Dark Justiciar"
  ],
  "Acolyte of Bahamut / Sivriss, Nightmare Speaker": [
    "Acolyte of Bahamut",
    "Sivriss, Nightmare Speaker"
  ],
  "Acolyte of Bahamut / Skanos Dragonheart": [
    "Acolyte of Bahamut",
    "Skanos Dragonheart"
  ],
  "Acolyte of Bahamut / Vhal, Candlekeep Researcher": [
    "Acolyte of Bahamut",
    "Vhal, Candlekeep Researcher"
  ],
  "Acolyte of Bahamut / Viconia, Drow Apostate": [
    "Acolyte of Bahamut",
    "Viconia, Drow Apostate"
  ],
  "Acolyte of Bahamut / Volo, Itinerant Scholar": [
    "Acolyte of Bahamut",
    "Volo, Itinerant Scholar"
  ],
  "Acolyte of Bahamut / Wilson, Refined Grizzly": [
    "Acolyte of Bahamut",
    "Wilson, Refined Grizzly"
  ],
  "Acolyte of Bahamut / Wyll, Blade of Frontiers": [
    "Acolyte of Bahamut",
    "Wyll, Blade of Frontiers"
  ],
  "Acolyte of Bahamut / Zellix, Sanity Flayer": [
    "Acolyte of Bahamut",
    "Zellix, Sanity Flayer"
  ],
  "Adric, Mathematical Genius / The Eighth Doctor": [
    "Adric, Mathematical Genius",
    "The Eighth Doctor"
  ],
  "Adric, Mathematical Genius / The Eleventh Doctor": [
    "Adric, Mathematical Genius",
    "The Eleventh Doctor"
  ],
  "Adric, Mathematical Genius / The Fifteenth Doctor": [
    "Adric, Mathematical Genius",
    "The Fifteenth Doctor"
  ],
  "Adric, Mathematical Genius / The Fifth Doctor": [
    "Adric, Mathematical Genius",
    "The Fifth Doctor"
  ],
  "Adric, Mathematical Genius / The First Doctor": [
    "Adric, Mathematical Genius",
    "The First Doctor"
  ],
  "Adric, Mathematical Genius / The Fourteenth Doctor": [
    "Adric, Mathematical Genius",
    "The Fourteenth Doctor"
  ],
  "Adric, Mathematical Genius / The Fourth Doctor": [
    "Adric, Mathematical Genius",
    "The Fourth Doctor"
  ],
  "Adric, Mathematical Genius / The Fugitive Doctor": [
    "Adric, Mathematical Genius",
    "The Fugitive Doctor"
  ],
  "Adric, Mathematical Genius / The Ninth Doctor": [
    "Adric, Mathematical Genius",
    "The Ninth Doctor"
  ],
  "Adric, Mathematical Genius / The Second Doctor": [
    "Adric, Mathematical Genius",
    "The Second Doctor"
  ],
  "Adric, Mathematical Genius / The Seventh Doctor": [
    "Adric, Mathematical Genius",
    "The Seventh Doctor"
  ],
  "Adric, Mathematical Genius / The Sixth Doctor": [
    "Adric, Mathematical Genius",
    "The Sixth Doctor"
  ],
  "Adric, Mathematical Genius / The Tenth Doctor": [
    "Adric, Mathematical Genius",
    "The Tenth Doctor"
  ],
  "Adric, Mathematical Genius / The Third Doctor": [
    "Adric, Mathematical Genius",
    "The Third Doctor"
  ],
  "Adric, Mathematical Genius / The Thirteenth Doctor": [
    "Adric, Mathematical Genius",
    "The Thirteenth Doctor"
  ],
  "Adric, Mathematical Genius / The Twelfth Doctor": [
    "Adric, Mathematical Genius",
    "The Twelfth Doctor"
  ],
  "Adric, Mathematical Genius / The War Doctor": [
    "Adric, Mathematical Genius",
    "The War Doctor"
  ],
  "Agent of the Iron Throne / Alora, Merry Thief": [
    "Agent of the Iron Throne",
    "Alora, Merry Thief"
  ],
  "Agent of the Iron Throne / Amber Gristle O'Maul": [
    "Agent of the Iron Throne",
    "Amber Gristle O'Maul"
  ],
  "Agent of the Iron Throne / Baeloth Barrityl, Entertainer": [
    "Agent of the Iron Throne",
    "Baeloth Barrityl, Entertainer"
  ],
  "Agent of the Iron Throne / Burakos, Party Leader": [
    "Agent of the Iron Throne",
    "Burakos, Party Leader"
  ],
  "Agent of the Iron Throne / Durnan of the Yawning Portal": [
    "Agent of the Iron Throne",
    "Durnan of the Yawning Portal"
  ],
  "Agent of the Iron Throne / Ellyn Harbreeze, Busybody": [
    "Agent of the Iron Throne",
    "Ellyn Harbreeze, Busybody"
  ],
  "Agent of the Iron Throne / Erinis, Gloom Stalker": [
    "Agent of the Iron Throne",
    "Erinis, Gloom Stalker"
  ],
  "Agent of the Iron Throne / Faceless One": [
    "Agent of the Iron Throne",
    "Faceless One"
  ],
  "Agent of the Iron Throne / Gale, Waterdeep Prodigy": [
    "Agent of the Iron Throne",
    "Gale, Waterdeep Prodigy"
  ],
  "Agent of the Iron Throne / Ganax, Astral Hunter": [
    "Agent of the Iron Throne",
    "Ganax, Astral Hunter"
  ],
  "Agent of the Iron Throne / Gut, True Soul Zealot": [
    "Agent of the Iron Throne",
    "Gut, True Soul Zealot"
  ],
  "Agent of the Iron Throne / Halsin, Emerald Archdruid": [
    "Agent of the Iron Throne",
    "Halsin, Emerald Archdruid"
  ],
  "Agent of the Iron Throne / Imoen, Mystic Trickster": [
    "Agent of the Iron Throne",
    "Imoen, Mystic Trickster"
  ],
  "Agent of the Iron Throne / Jaheira, Friend of the Forest": [
    "Agent of the Iron Throne",
    "Jaheira, Friend of the Forest"
  ],
  "Agent of the Iron Throne / Karlach, Fury of Avernus": [
    "Agent of the Iron Throne",
    "Karlach, Fury of Avernus"
  ],
  "Agent of the Iron Throne / Lae'zel, Vlaakith's Champion": [
    "Agent of the Iron Throne",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Agent of the Iron Throne / Livaan, Cultist of Tiamat": [
    "Agent of the Iron Throne",
    "Livaan, Cultist of Tiamat"
  ],
  "Agent of the Iron Throne / Lulu, Loyal Hollyphant": [
    "Agent of the Iron Throne",
    "Lulu, Loyal Hollyphant"
  ],
  "Agent of the Iron Throne / Rasaad yn Bashir": [
    "Agent of the Iron Throne",
    "Rasaad yn Bashir"
  ],
  "Agent of the Iron Throne / Renari, Merchant of Marvels": [
    "Agent of the Iron Throne",
    "Renari, Merchant of Marvels"
  ],
  "Agent of the Iron Throne / Safana, Calimport Cutthroat": [
    "Agent of the Iron Throne",
    "Safana, Calimport Cutthroat"
  ],
  "Agent of the Iron Throne / Sarevok, Deathbringer": [
    "Agent of the Iron Throne",
    "Sarevok, Deathbringer"
  ],
  "Agent of the Iron Throne / Shadowheart, Dark Justiciar": [
    "Agent of the Iron Throne",
    "Shadowheart, Dark Justiciar"
  ],
  "Agent of the Iron Throne / Sivriss, Nightmare Speaker": [
    "Agent of the Iron Throne",
    "Sivriss, Nightmare Speaker"
  ],
  "Agent of the Iron Throne / Skanos Dragonheart": [
    "Agent of the Iron Throne",
    "Skanos Dragonheart"
  ],
  "Agent of the Iron Throne / Vhal, Candlekeep Researcher": [
    "Agent of the Iron Throne",
    "Vhal, Candlekeep Researcher"
  ],
  "Agent of the Iron Throne / Viconia, Drow Apostate": [
    "Agent of the Iron Throne",
    "Viconia, Drow Apostate"
  ],
  "Agent of the Iron Throne / Volo, Itinerant Scholar": [
    "Agent of the Iron Throne",
    "Volo, Itinerant Scholar"
  ],
  "Agent of the Iron Throne / Wilson, Refined Grizzly": [
    "Agent of the Iron Throne",
    "Wilson, Refined Grizzly"
  ],
  "Agent of the Iron Throne / Wyll, Blade of Frontiers": [
    "Agent of the Iron Throne",
    "Wyll, Blade of Frontiers"
  ],
  "Agent of the Iron Throne / Zellix, Sanity Flayer": [
    "Agent of the Iron Throne",
    "Zellix, Sanity Flayer"
  ],
  "Agent of the Shadow Thieves / Alora, Merry Thief": [
    "Agent of the Shadow Thieves",
    "Alora, Merry Thief"
  ],
  "Agent of the Shadow Thieves / Amber Gristle O'Maul": [
    "Agent of the Shadow Thieves",
    "Amber Gristle O'Maul"
  ],
  "Agent of the Shadow Thieves / Baeloth Barrityl, Entertainer": [
    "Agent of the Shadow Thieves",
    "Baeloth Barrityl, Entertainer"
  ],
  "Agent of the Shadow Thieves / Burakos, Party Leader": [
    "Agent of the Shadow Thieves",
    "Burakos, Party Leader"
  ],
  "Agent of the Shadow Thieves / Durnan of the Yawning Portal": [
    "Agent of the Shadow Thieves",
    "Durnan of the Yawning Portal"
  ],
  "Agent of the Shadow Thieves / Ellyn Harbreeze, Busybody": [
    "Agent of the Shadow Thieves",
    "Ellyn Harbreeze, Busybody"
  ],
  "Agent of the Shadow Thieves / Erinis, Gloom Stalker": [
    "Agent of the Shadow Thieves",
    "Erinis, Gloom Stalker"
  ],
  "Agent of the Shadow Thieves / Faceless One": [
    "Agent of the Shadow Thieves",
    "Faceless One"
  ],
  "Agent of the Shadow Thieves / Gale, Waterdeep Prodigy": [
    "Agent of the Shadow Thieves",
    "Gale, Waterdeep Prodigy"
  ],
  "Agent of the Shadow Thieves / Ganax, Astral Hunter": [
    "Agent of the Shadow Thieves",
    "Ganax, Astral Hunter"
  ],
  "Agent of the Shadow Thieves / Gut, True Soul Zealot": [
    "Agent of the Shadow Thieves",
    "Gut, True Soul Zealot"
  ],
  "Agent of the Shadow Thieves / Halsin, Emerald Archdruid": [
    "Agent of the Shadow Thieves",
    "Halsin, Emerald Archdruid"
  ],
  "Agent of the Shadow Thieves / Imoen, Mystic Trickster": [
    "Agent of the Shadow Thieves",
    "Imoen, Mystic Trickster"
  ],
  "Agent of the Shadow Thieves / Jaheira, Friend of the Forest": [
    "Agent of the Shadow Thieves",
    "Jaheira, Friend of the Forest"
  ],
  "Agent of the Shadow Thieves / Karlach, Fury of Avernus": [
    "Agent of the Shadow Thieves",
    "Karlach, Fury of Avernus"
  ],
  "Agent of the Shadow Thieves / Lae'zel, Vlaakith's Champion": [
    "Agent of the Shadow Thieves",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Agent of the Shadow Thieves / Livaan, Cultist of Tiamat": [
    "Agent of the Shadow Thieves",
    "Livaan, Cultist of Tiamat"
  ],
  "Agent of the Shadow Thieves / Lulu, Loyal Hollyphant": [
    "Agent of the Shadow Thieves",
    "Lulu, Loyal Hollyphant"
  ],
  "Agent of the Shadow Thieves / Rasaad yn Bashir": [
    "Agent of the Shadow Thieves",
    "Rasaad yn Bashir"
  ],
  "Agent of the Shadow Thieves / Renari, Merchant of Marvels": [
    "Agent of the Shadow Thieves",
    "Renari, Merchant of Marvels"
  ],
  "Agent of the Shadow Thieves / Safana, Calimport Cutthroat": [
    "Agent of the Shadow Thieves",
    "Safana, Calimport Cutthroat"
  ],
  "Agent of the Shadow Thieves / Sarevok, Deathbringer": [
    "Agent of the Shadow Thieves",
    "Sarevok, Deathbringer"
  ],
  "Agent of the Shadow Thieves / Shadowheart, Dark Justiciar": [
    "Agent of the Shadow Thieves",
    "Shadowheart, Dark Justiciar"
  ],
  "Agent of the Shadow Thieves / Sivriss, Nightmare Speaker": [
    "Agent of the Shadow Thieves",
    "Sivriss, Nightmare Speaker"
  ],
  "Agent of the Shadow Thieves / Skanos Dragonheart": [
    "Agent of the Shadow Thieves",
    "Skanos Dragonheart"
  ],
  "Agent of the Shadow Thieves / Vhal, Candlekeep Researcher": [
    "Agent of the Shadow Thieves",
    "Vhal, Candlekeep Researcher"
  ],
  "Agent of the Shadow Thieves / Viconia, Drow Apostate": [
    "Agent of the Shadow Thieves",
    "Viconia, Drow Apostate"
  ],
  "Agent of the Shadow Thieves / Volo, Itinerant Scholar": [
    "Agent of the Shadow Thieves",
    "Volo, Itinerant Scholar"
  ],
  "Agent of the Shadow Thieves / Wilson, Refined Grizzly": [
    "Agent of the Shadow Thieves",
    "Wilson, Refined Grizzly"
  ],
  "Agent of the Shadow Thieves / Wyll, Blade of Frontiers": [
    "Agent of the Shadow Thieves",
    "Wyll, Blade of Frontiers"
  ],
  "Agent of the Shadow Thieves / Zellix, Sanity Flayer": [
    "Agent of the Shadow Thieves",
    "Zellix, Sanity Flayer"
  ],
  "Akiri, Line-Slinger / Akroma, Vision of Ixidor": [
    "Akiri, Line-Slinger",
    "Akroma, Vision of Ixidor"
  ],
  "Akiri, Line-Slinger / Alena, Kessig Trapper": [
    "Akiri, Line-Slinger",
    "Alena, Kessig Trapper"
  ],
  "Akiri, Line-Slinger / Alharu, Solemn Ritualist": [
    "Akiri, Line-Slinger",
    "Alharu, Solemn Ritualist"
  ],
  "Akiri, Line-Slinger / Anara, Wolvid Familiar": [
    "Akiri, Line-Slinger",
    "Anara, Wolvid Familiar"
  ],
  "Akiri, Line-Slinger / Ardenn, Intrepid Archaeologist": [
    "Akiri, Line-Slinger",
    "Ardenn, Intrepid Archaeologist"
  ],
  "Akiri, Line-Slinger / Armix, Filigree Thrasher": [
    "Akiri, Line-Slinger",
    "Armix, Filigree Thrasher"
  ],
  "Akiri, Line-Slinger / Breeches, Brazen Plunderer": [
    "Akiri, Line-Slinger",
    "Breeches, Brazen Plunderer"
  ],
  "Akiri, Line-Slinger / Brinelin, the Moon Kraken": [
    "Akiri, Line-Slinger",
    "Brinelin, the Moon Kraken"
  ],
  "Akiri, Line-Slinger / Bruse Tarl, Boorish Herder": [
    "Akiri, Line-Slinger",
    "Bruse Tarl, Boorish Herder"
  ],
  "Akiri, Line-Slinger / Dargo, the Shipwrecker": [
    "Akiri, Line-Slinger",
    "Dargo, the Shipwrecker"
  ],
  "Akiri, Line-Slinger / Eligeth, Crossroads Augur": [
    "Akiri, Line-Slinger",
    "Eligeth, Crossroads Augur"
  ],
  "Akiri, Line-Slinger / Esior, Wardwing Familiar": [
    "Akiri, Line-Slinger",
    "Esior, Wardwing Familiar"
  ],
  "Akiri, Line-Slinger / Falthis, Shadowcat Familiar": [
    "Akiri, Line-Slinger",
    "Falthis, Shadowcat Familiar"
  ],
  "Akiri, Line-Slinger / Francisco, Fowl Marauder": [
    "Akiri, Line-Slinger",
    "Francisco, Fowl Marauder"
  ],
  "Akiri, Line-Slinger / Ghost of Ramirez DePietro": [
    "Akiri, Line-Slinger",
    "Ghost of Ramirez DePietro"
  ],
  "Akiri, Line-Slinger / Gilanra, Caller of Wirewood": [
    "Akiri, Line-Slinger",
    "Gilanra, Caller of Wirewood"
  ],
  "Akiri, Line-Slinger / Glacian, Powerstone Engineer": [
    "Akiri, Line-Slinger",
    "Glacian, Powerstone Engineer"
  ],
  "Akiri, Line-Slinger / Halana, Kessig Ranger": [
    "Akiri, Line-Slinger",
    "Halana, Kessig Ranger"
  ],
  "Akiri, Line-Slinger / Ich-Tekik, Salvage Splicer": [
    "Akiri, Line-Slinger",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Akiri, Line-Slinger / Ikra Shidiqi, the Usurper": [
    "Akiri, Line-Slinger",
    "Ikra Shidiqi, the Usurper"
  ],
  "Akiri, Line-Slinger / Ishai, Ojutai Dragonspeaker": [
    "Akiri, Line-Slinger",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Akiri, Line-Slinger / Jeska, Thrice Reborn": [
    "Akiri, Line-Slinger",
    "Jeska, Thrice Reborn"
  ],
  "Akiri, Line-Slinger / Kamahl, Heart of Krosa": [
    "Akiri, Line-Slinger",
    "Kamahl, Heart of Krosa"
  ],
  "Akiri, Line-Slinger / Kediss, Emberclaw Familiar": [
    "Akiri, Line-Slinger",
    "Kediss, Emberclaw Familiar"
  ],
  "Akiri, Line-Slinger / Keleth, Sunmane Familiar": [
    "Akiri, Line-Slinger",
    "Keleth, Sunmane Familiar"
  ],
  "Akiri, Line-Slinger / Keskit, the Flesh Sculptor": [
    "Akiri, Line-Slinger",
    "Keskit, the Flesh Sculptor"
  ],
  "Akiri, Line-Slinger / Kodama of the East Tree": [
    "Akiri, Line-Slinger",
    "Kodama of the East Tree"
  ],
  "Akiri, Line-Slinger / Krark, the Thumbless": [
    "Akiri, Line-Slinger",
    "Krark, the Thumbless"
  ],
  "Akiri, Line-Slinger / Kraum, Ludevic's Opus": [
    "Akiri, Line-Slinger",
    "Kraum, Ludevic's Opus"
  ],
  "Akiri, Line-Slinger / Kydele, Chosen of Kruphix": [
    "Akiri, Line-Slinger",
    "Kydele, Chosen of Kruphix"
  ],
  "Akiri, Line-Slinger / Livio, Oathsworn Sentinel": [
    "Akiri, Line-Slinger",
    "Livio, Oathsworn Sentinel"
  ],
  "Akiri, Line-Slinger / Ludevic, Necro-Alchemist": [
    "Akiri, Line-Slinger",
    "Ludevic, Necro-Alchemist"
  ],
  "Akiri, Line-Slinger / Malcolm, Keen-Eyed Navigator": [
    "Akiri, Line-Slinger",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Akiri, Line-Slinger / Miara, Thorn of the Glade": [
    "Akiri, Line-Slinger",
    "Miara, Thorn of the Glade"
  ],
  "Akiri, Line-Slinger / Nadier, Agent of the Duskenel": [
    "Akiri, Line-Slinger",
    "Nadier, Agent of the Duskenel"
  ],
  "Akiri, Line-Slinger / Numa, Joraga Chieftain": [
    "Akiri, Line-Slinger",
    "Numa, Joraga Chieftain"
  ],
  "Akiri, Line-Slinger / Prava of the Steel Legion": [
    "Akiri, Line-Slinger",
    "Prava of the Steel Legion"
  ],
  "Akiri, Line-Slinger / Radiant, Serra Archangel": [
    "Akiri, Line-Slinger",
    "Radiant, Serra Archangel"
  ],
  "Akiri, Line-Slinger / Ravos, Soultender": [
    "Akiri, Line-Slinger",
    "Ravos, Soultender"
  ],
  "Akiri, Line-Slinger / Rebbec, Architect of Ascension": [
    "Akiri, Line-Slinger",
    "Rebbec, Architect of Ascension"
  ],
  "Akiri, Line-Slinger / Reyhan, Last of the Abzan": [
    "Akiri, Line-Slinger",
    "Reyhan, Last of the Abzan"
  ],
  "Akiri, Line-Slinger / Rograkh, Son of Rohgahh": [
    "Akiri, Line-Slinger",
    "Rograkh, Son of Rohgahh"
  ],
  "Akiri, Line-Slinger / Sakashima of a Thousand Faces": [
    "Akiri, Line-Slinger",
    "Sakashima of a Thousand Faces"
  ],
  "Akiri, Line-Slinger / Sengir, the Dark Baron": [
    "Akiri, Line-Slinger",
    "Sengir, the Dark Baron"
  ],
  "Akiri, Line-Slinger / Siani, Eye of the Storm": [
    "Akiri, Line-Slinger",
    "Siani, Eye of the Storm"
  ],
  "Akiri, Line-Slinger / Sidar Kondo of Jamuraa": [
    "Akiri, Line-Slinger",
    "Sidar Kondo of Jamuraa"
  ],
  "Akiri, Line-Slinger / Silas Renn, Seeker Adept": [
    "Akiri, Line-Slinger",
    "Silas Renn, Seeker Adept"
  ],
  "Akiri, Line-Slinger / Slurrk, All-Ingesting": [
    "Akiri, Line-Slinger",
    "Slurrk, All-Ingesting"
  ],
  "Akiri, Line-Slinger / Tana, the Bloodsower": [
    "Akiri, Line-Slinger",
    "Tana, the Bloodsower"
  ],
  "Akiri, Line-Slinger / Tevesh Szat, Doom of Fools": [
    "Akiri, Line-Slinger",
    "Tevesh Szat, Doom of Fools"
  ],
  "Akiri, Line-Slinger / The Prismatic Piper": [
    "Akiri, Line-Slinger",
    "The Prismatic Piper"
  ],
  "Akiri, Line-Slinger / Thrasios, Triton Hero": [
    "Akiri, Line-Slinger",
    "Thrasios, Triton Hero"
  ],
  "Akiri, Line-Slinger / Toggo, Goblin Weaponsmith": [
    "Akiri, Line-Slinger",
    "Toggo, Goblin Weaponsmith"
  ],
  "Akiri, Line-Slinger / Tormod, the Desecrator": [
    "Akiri, Line-Slinger",
    "Tormod, the Desecrator"
  ],
  "Akiri, Line-Slinger / Tymna the Weaver": [
    "Akiri, Line-Slinger",
    "Tymna the Weaver"
  ],
  "Akiri, Line-Slinger / Vial Smasher the Fierce": [
    "Akiri, Line-Slinger",
    "Vial Smasher the Fierce"
  ],
  "Akiri, Line-Slinger / Yoshimaru, Ever Faithful": [
    "Akiri, Line-Slinger",
    "Yoshimaru, Ever Faithful"
  ],
  "Akroma, Vision of Ixidor / Alena, Kessig Trapper": [
    "Akroma, Vision of Ixidor",
    "Alena, Kessig Trapper"
  ],
  "Akroma, Vision of Ixidor / Alharu, Solemn Ritualist": [
    "Akroma, Vision of Ixidor",
    "Alharu, Solemn Ritualist"
  ],
  "Akroma, Vision of Ixidor / Anara, Wolvid Familiar": [
    "Akroma, Vision of Ixidor",
    "Anara, Wolvid Familiar"
  ],
  "Akroma, Vision of Ixidor / Ardenn, Intrepid Archaeologist": [
    "Akroma, Vision of Ixidor",
    "Ardenn, Intrepid Archaeologist"
  ],
  "Akroma, Vision of Ixidor / Armix, Filigree Thrasher": [
    "Akroma, Vision of Ixidor",
    "Armix, Filigree Thrasher"
  ],
  "Akroma, Vision of Ixidor / Breeches, Brazen Plunderer": [
    "Akroma, Vision of Ixidor",
    "Breeches, Brazen Plunderer"
  ],
  "Akroma, Vision of Ixidor / Brinelin, the Moon Kraken": [
    "Akroma, Vision of Ixidor",
    "Brinelin, the Moon Kraken"
  ],
  "Akroma, Vision of Ixidor / Bruse Tarl, Boorish Herder": [
    "Akroma, Vision of Ixidor",
    "Bruse Tarl, Boorish Herder"
  ],
  "Akroma, Vision of Ixidor / Dargo, the Shipwrecker": [
    "Akroma, Vision of Ixidor",
    "Dargo, the Shipwrecker"
  ],
  "Akroma, Vision of Ixidor / Eligeth, Crossroads Augur": [
    "Akroma, Vision of Ixidor",
    "Eligeth, Crossroads Augur"
  ],
  "Akroma, Vision of Ixidor / Esior, Wardwing Familiar": [
    "Akroma, Vision of Ixidor",
    "Esior, Wardwing Familiar"
  ],
  "Akroma, Vision of Ixidor / Falthis, Shadowcat Familiar": [
    "Akroma, Vision of Ixidor",
    "Falthis, Shadowcat Familiar"
  ],
  "Akroma, Vision of Ixidor / Francisco, Fowl Marauder": [
    "Akroma, Vision of Ixidor",
    "Francisco, Fowl Marauder"
  ],
  "Akroma, Vision of Ixidor / Ghost of Ramirez DePietro": [
    "Akroma, Vision of Ixidor",
    "Ghost of Ramirez DePietro"
  ],
  "Akroma, Vision of Ixidor / Gilanra, Caller of Wirewood": [
    "Akroma, Vision of Ixidor",
    "Gilanra, Caller of Wirewood"
  ],
  "Akroma, Vision of Ixidor / Glacian, Powerstone Engineer": [
    "Akroma, Vision of Ixidor",
    "Glacian, Powerstone Engineer"
  ],
  "Akroma, Vision of Ixidor / Halana, Kessig Ranger": [
    "Akroma, Vision of Ixidor",
    "Halana, Kessig Ranger"
  ],
  "Akroma, Vision of Ixidor / Ich-Tekik, Salvage Splicer": [
    "Akroma, Vision of Ixidor",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Akroma, Vision of Ixidor / Ikra Shidiqi, the Usurper": [
    "Akroma, Vision of Ixidor",
    "Ikra Shidiqi, the Usurper"
  ],
  "Akroma, Vision of Ixidor / Ishai, Ojutai Dragonspeaker": [
    "Akroma, Vision of Ixidor",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Akroma, Vision of Ixidor / Jeska, Thrice Reborn": [
    "Akroma, Vision of Ixidor",
    "Jeska, Thrice Reborn"
  ],
  "Akroma, Vision of Ixidor / Kamahl, Heart of Krosa": [
    "Akroma, Vision of Ixidor",
    "Kamahl, Heart of Krosa"
  ],
  "Akroma, Vision of Ixidor / Kediss, Emberclaw Familiar": [
    "Akroma, Vision of Ixidor",
    "Kediss, Emberclaw Familiar"
  ],
  "Akroma, Vision of Ixidor / Keleth, Sunmane Familiar": [
    "Akroma, Vision of Ixidor",
    "Keleth, Sunmane Familiar"
  ],
  "Akroma, Vision of Ixidor / Keskit, the Flesh Sculptor": [
    "Akroma, Vision of Ixidor",
    "Keskit, the Flesh Sculptor"
  ],
  "Akroma, Vision of Ixidor / Kodama of the East Tree": [
    "Akroma, Vision of Ixidor",
    "Kodama of the East Tree"
  ],
  "Akroma, Vision of Ixidor / Krark, the Thumbless": [
    "Akroma, Vision of Ixidor",
    "Krark, the Thumbless"
  ],
  "Akroma, Vision of Ixidor / Kraum, Ludevic's Opus": [
    "Akroma, Vision of Ixidor",
    "Kraum, Ludevic's Opus"
  ],
  "Akroma, Vision of Ixidor / Kydele, Chosen of Kruphix": [
    "Akroma, Vision of Ixidor",
    "Kydele, Chosen of Kruphix"
  ],
  "Akroma, Vision of Ixidor / Livio, Oathsworn Sentinel": [
    "Akroma, Vision of Ixidor",
    "Livio, Oathsworn Sentinel"
  ],
  "Akroma, Vision of Ixidor / Ludevic, Necro-Alchemist": [
    "Akroma, Vision of Ixidor",
    "Ludevic, Necro-Alchemist"
  ],
  "Akroma, Vision of Ixidor / Malcolm, Keen-Eyed Navigator": [
    "Akroma, Vision of Ixidor",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Akroma, Vision of Ixidor / Miara, Thorn of the Glade": [
    "Akroma, Vision of Ixidor",
    "Miara, Thorn of the Glade"
  ],
  "Akroma, Vision of Ixidor / Nadier, Agent of the Duskenel": [
    "Akroma, Vision of Ixidor",
    "Nadier, Agent of the Duskenel"
  ],
  "Akroma, Vision of Ixidor / Numa, Joraga Chieftain": [
    "Akroma, Vision of Ixidor",
    "Numa, Joraga Chieftain"
  ],
  "Akroma, Vision of Ixidor / Prava of the Steel Legion": [
    "Akroma, Vision of Ixidor",
    "Prava of the Steel Legion"
  ],
  "Akroma, Vision of Ixidor / Radiant, Serra Archangel": [
    "Akroma, Vision of Ixidor",
    "Radiant, Serra Archangel"
  ],
  "Akroma, Vision of Ixidor / Ravos, Soultender": [
    "Akroma, Vision of Ixidor",
    "Ravos, Soultender"
  ],
  "Akroma, Vision of Ixidor / Rebbec, Architect of Ascension": [
    "Akroma, Vision of Ixidor",
    "Rebbec, Architect of Ascension"
  ],
  "Akroma, Vision of Ixidor / Reyhan, Last of the Abzan": [
    "Akroma, Vision of Ixidor",
    "Reyhan, Last of the Abzan"
  ],
  "Akroma, Vision of Ixidor / Rograkh, Son of Rohgahh": [
    "Akroma, Vision of Ixidor",
    "Rograkh, Son of Rohgahh"
  ],
  "Akroma, Vision of Ixidor / Sakashima of a Thousand Faces": [
    "Akroma, Vision of Ixidor",
    "Sakashima of a Thousand Faces"
  ],
  "Akroma, Vision of Ixidor / Sengir, the Dark Baron": [
    "Akroma, Vision of Ixidor",
    "Sengir, the Dark Baron"
  ],
  "Akroma, Vision of Ixidor / Siani, Eye of the Storm": [
    "Akroma, Vision of Ixidor",
    "Siani, Eye of the Storm"
  ],
  "Akroma, Vision of Ixidor / Sidar Kondo of Jamuraa": [
    "Akroma, Vision of Ixidor",
    "Sidar Kondo of Jamuraa"
  ],
  "Akroma, Vision of Ixidor / Silas Renn, Seeker Adept": [
    "Akroma, Vision of Ixidor",
    "Silas Renn, Seeker Adept"
  ],
  "Akroma, Vision of Ixidor / Slurrk, All-Ingesting": [
    "Akroma, Vision of Ixidor",
    "Slurrk, All-Ingesting"
  ],
  "Akroma, Vision of Ixidor / Tana, the Bloodsower": [
    "Akroma, Vision of Ixidor",
    "Tana, the Bloodsower"
  ],
  "Akroma, Vision of Ixidor / Tevesh Szat, Doom of Fools": [
    "Akroma, Vision of Ixidor",
    "Tevesh Szat, Doom of Fools"
  ],
  "Akroma, Vision of Ixidor / The Prismatic Piper": [
    "Akroma, Vision of Ixidor",
    "The Prismatic Piper"
  ],
  "Akroma, Vision of Ixidor / Thrasios, Triton Hero": [
    "Akroma, Vision of Ixidor",
    "Thrasios, Triton Hero"
  ],
  "Akroma, Vision of Ixidor / Toggo, Goblin Weaponsmith": [
    "Akroma, Vision of Ixidor",
    "Toggo, Goblin Weaponsmith"
  ],
  "Akroma, Vision of Ixidor / Tormod, the Desecrator": [
    "Akroma, Vision of Ixidor",
    "Tormod, the Desecrator"
  ],
  "Akroma, Vision of Ixidor / Tymna the Weaver": [
    "Akroma, Vision of Ixidor",
    "Tymna the Weaver"
  ],
  "Akroma, Vision of Ixidor / Vial Smasher the Fierce": [
    "Akroma, Vision of Ixidor",
    "Vial Smasher the Fierce"
  ],
  "Akroma, Vision of Ixidor / Yoshimaru, Ever Faithful": [
    "Akroma, Vision of Ixidor",
    "Yoshimaru, Ever Faithful"
  ],
  "Alena, Kessig Trapper / Alharu, Solemn Ritualist": [
    "Alena, Kessig Trapper",
    "Alharu, Solemn Ritualist"
  ],
  "Alena, Kessig Trapper / Anara, Wolvid Familiar": [
    "Alena, Kessig Trapper",
    "Anara, Wolvid Familiar"
  ],
  "Alena, Kessig Trapper / Ardenn, Intrepid Archaeologist": [
    "Alena, Kessig Trapper",
    "Ardenn, Intrepid Archaeologist"
  ],
  "Alena, Kessig Trapper / Armix, Filigree Thrasher": [
    "Alena, Kessig Trapper",
    "Armix, Filigree Thrasher"
  ],
  "Alena, Kessig Trapper / Breeches, Brazen Plunderer": [
    "Alena, Kessig Trapper",
    "Breeches, Brazen Plunderer"
  ],
  "Alena, Kessig Trapper / Brinelin, the Moon Kraken": [
    "Alena, Kessig Trapper",
    "Brinelin, the Moon Kraken"
  ],
  "Alena, Kessig Trapper / Bruse Tarl, Boorish Herder": [
    "Alena, Kessig Trapper",
    "Bruse Tarl, Boorish Herder"
  ],
  "Alena, Kessig Trapper / Dargo, the Shipwrecker": [
    "Alena, Kessig Trapper",
    "Dargo, the Shipwrecker"
  ],
  "Alena, Kessig Trapper / Eligeth, Crossroads Augur": [
    "Alena, Kessig Trapper",
    "Eligeth, Crossroads Augur"
  ],
  "Alena, Kessig Trapper / Esior, Wardwing Familiar": [
    "Alena, Kessig Trapper",
    "Esior, Wardwing Familiar"
  ],
  "Alena, Kessig Trapper / Falthis, Shadowcat Familiar": [
    "Alena, Kessig Trapper",
    "Falthis, Shadowcat Familiar"
  ],
  "Alena, Kessig Trapper / Francisco, Fowl Marauder": [
    "Alena, Kessig Trapper",
    "Francisco, Fowl Marauder"
  ],
  "Alena, Kessig Trapper / Ghost of Ramirez DePietro": [
    "Alena, Kessig Trapper",
    "Ghost of Ramirez DePietro"
  ],
  "Alena, Kessig Trapper / Gilanra, Caller of Wirewood": [
    "Alena, Kessig Trapper",
    "Gilanra, Caller of Wirewood"
  ],
  "Alena, Kessig Trapper / Glacian, Powerstone Engineer": [
    "Alena, Kessig Trapper",
    "Glacian, Powerstone Engineer"
  ],
  "Alena, Kessig Trapper / Halana, Kessig Ranger": [
    "Alena, Kessig Trapper",
    "Halana, Kessig Ranger"
  ],
  "Alena, Kessig Trapper / Ich-Tekik, Salvage Splicer": [
    "Alena, Kessig Trapper",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Alena, Kessig Trapper / Ikra Shidiqi, the Usurper": [
    "Alena, Kessig Trapper",
    "Ikra Shidiqi, the Usurper"
  ],
  "Alena, Kessig Trapper / Ishai, Ojutai Dragonspeaker": [
    "Alena, Kessig Trapper",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Alena, Kessig Trapper / Jeska, Thrice Reborn": [
    "Alena, Kessig Trapper",
    "Jeska, Thrice Reborn"
  ],
  "Alena, Kessig Trapper / Kamahl, Heart of Krosa": [
    "Alena, Kessig Trapper",
    "Kamahl, Heart of Krosa"
  ],
  "Alena, Kessig Trapper / Kediss, Emberclaw Familiar": [
    "Alena, Kessig Trapper",
    "Kediss, Emberclaw Familiar"
  ],
  "Alena, Kessig Trapper / Keleth, Sunmane Familiar": [
    "Alena, Kessig Trapper",
    "Keleth, Sunmane Familiar"
  ],
  "Alena, Kessig Trapper / Keskit, the Flesh Sculptor": [
    "Alena, Kessig Trapper",
    "Keskit, the Flesh Sculptor"
  ],
  "Alena, Kessig Trapper / Kodama of the East Tree": [
    "Alena, Kessig Trapper",
    "Kodama of the East Tree"
  ],
  "Alena, Kessig Trapper / Krark, the Thumbless": [
    "Alena, Kessig Trapper",
    "Krark, the Thumbless"
  ],
  "Alena, Kessig Trapper / Kraum, Ludevic's Opus": [
    "Alena, Kessig Trapper",
    "Kraum, Ludevic's Opus"
  ],
  "Alena, Kessig Trapper / Kydele, Chosen of Kruphix": [
    "Alena, Kessig Trapper",
    "Kydele, Chosen of Kruphix"
  ],
  "Alena, Kessig Trapper / Livio, Oathsworn Sentinel": [
    "Alena, Kessig Trapper",
    "Livio, Oathsworn Sentinel"
  ],
  "Alena, Kessig Trapper / Ludevic, Necro-Alchemist": [
    "Alena, Kessig Trapper",
    "Ludevic, Necro-Alchemist"
  ],
  "Alena, Kessig Trapper / Malcolm, Keen-Eyed Navigator": [
    "Alena, Kessig Trapper",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Alena, Kessig Trapper / Miara, Thorn of the Glade": [
    "Alena, Kessig Trapper",
    "Miara, Thorn of the Glade"
  ],
  "Alena, Kessig Trapper / Nadier, Agent of the Duskenel": [
    "Alena, Kessig Trapper",
    "Nadier, Agent of the Duskenel"
  ],
  "Alena, Kessig Trapper / Numa, Joraga Chieftain": [
    "Alena, Kessig Trapper",
    "Numa, Joraga Chieftain"
  ],
  "Alena, Kessig Trapper / Prava of the Steel Legion": [
    "Alena, Kessig Trapper",
    "Prava of the Steel Legion"
  ],
  "Alena, Kessig Trapper / Radiant, Serra Archangel": [
    "Alena, Kessig Trapper",
    "Radiant, Serra Archangel"
  ],
  "Alena, Kessig Trapper / Ravos, Soultender": [
    "Alena, Kessig Trapper",
    "Ravos, Soultender"
  ],
  "Alena, Kessig Trapper / Rebbec, Architect of Ascension": [
    "Alena, Kessig Trapper",
    "Rebbec, Architect of Ascension"
  ],
  "Alena, Kessig Trapper / Reyhan, Last of the Abzan": [
    "Alena, Kessig Trapper",
    "Reyhan, Last of the Abzan"
  ],
  "Alena, Kessig Trapper / Rograkh, Son of Rohgahh": [
    "Alena, Kessig Trapper",
    "Rograkh, Son of Rohgahh"
  ],
  "Alena, Kessig Trapper / Sakashima of a Thousand Faces": [
    "Alena, Kessig Trapper",
    "Sakashima of a Thousand Faces"
  ],
  "Alena, Kessig Trapper / Sengir, the Dark Baron": [
    "Alena, Kessig Trapper",
    "Sengir, the Dark Baron"
  ],
  "Alena, Kessig Trapper / Siani, Eye of the Storm": [
    "Alena, Kessig Trapper",
    "Siani, Eye of the Storm"
  ],
  "Alena, Kessig Trapper / Sidar Kondo of Jamuraa": [
    "Alena, Kessig Trapper",
    "Sidar Kondo of Jamuraa"
  ],
  "Alena, Kessig Trapper / Silas Renn, Seeker Adept": [
    "Alena, Kessig Trapper",
    "Silas Renn, Seeker Adept"
  ],
  "Alena, Kessig Trapper / Slurrk, All-Ingesting": [
    "Alena, Kessig Trapper",
    "Slurrk, All-Ingesting"
  ],
  "Alena, Kessig Trapper / Tana, the Bloodsower": [
    "Alena, Kessig Trapper",
    "Tana, the Bloodsower"
  ],
  "Alena, Kessig Trapper / Tevesh Szat, Doom of Fools": [
    "Alena, Kessig Trapper",
    "Tevesh Szat, Doom of Fools"
  ],
  "Alena, Kessig Trapper / The Prismatic Piper": [
    "Alena, Kessig Trapper",
    "The Prismatic Piper"
  ],
  "Alena, Kessig Trapper / Thrasios, Triton Hero": [
    "Alena, Kessig Trapper",
    "Thrasios, Triton Hero"
  ],
  "Alena, Kessig Trapper / Toggo, Goblin Weaponsmith": [
    "Alena, Kessig Trapper",
    "Toggo, Goblin Weaponsmith"
  ],
  "Alena, Kessig Trapper / Tormod, the Desecrator": [
    "Alena, Kessig Trapper",
    "Tormod, the Desecrator"
  ],
  "Alena, Kessig Trapper / Tymna the Weaver": [
    "Alena, Kessig Trapper",
    "Tymna the Weaver"
  ],
  "Alena, Kessig Trapper / Vial Smasher the Fierce": [
    "Alena, Kessig Trapper",
    "Vial Smasher the Fierce"
  ],
  "Alena, Kessig Trapper / Yoshimaru, Ever Faithful": [
    "Alena, Kessig Trapper",
    "Yoshimaru, Ever Faithful"
  ],
  "Alharu, Solemn Ritualist / Anara, Wolvid Familiar": [
    "Alharu, Solemn Ritualist",
    "Anara, Wolvid Familiar"
  ],
  "Alharu, Solemn Ritualist / Ardenn, Intrepid Archaeologist": [
    "Alharu, Solemn Ritualist",
    "Ardenn, Intrepid Archaeologist"
  ],
  "Alharu, Solemn Ritualist / Armix, Filigree Thrasher": [
    "Alharu, Solemn Ritualist",
    "Armix, Filigree Thrasher"
  ],
  "Alharu, Solemn Ritualist / Breeches, Brazen Plunderer": [
    "Alharu, Solemn Ritualist",
    "Breeches, Brazen Plunderer"
  ],
  "Alharu, Solemn Ritualist / Brinelin, the Moon Kraken": [
    "Alharu, Solemn Ritualist",
    "Brinelin, the Moon Kraken"
  ],
  "Alharu, Solemn Ritualist / Bruse Tarl, Boorish Herder": [
    "Alharu, Solemn Ritualist",
    "Bruse Tarl, Boorish Herder"
  ],
  "Alharu, Solemn Ritualist / Dargo, the Shipwrecker": [
    "Alharu, Solemn Ritualist",
    "Dargo, the Shipwrecker"
  ],
  "Alharu, Solemn Ritualist / Eligeth, Crossroads Augur": [
    "Alharu, Solemn Ritualist",
    "Eligeth, Crossroads Augur"
  ],
  "Alharu, Solemn Ritualist / Esior, Wardwing Familiar": [
    "Alharu, Solemn Ritualist",
    "Esior, Wardwing Familiar"
  ],
  "Alharu, Solemn Ritualist / Falthis, Shadowcat Familiar": [
    "Alharu, Solemn Ritualist",
    "Falthis, Shadowcat Familiar"
  ],
  "Alharu, Solemn Ritualist / Francisco, Fowl Marauder": [
    "Alharu, Solemn Ritualist",
    "Francisco, Fowl Marauder"
  ],
  "Alharu, Solemn Ritualist / Ghost of Ramirez DePietro": [
    "Alharu, Solemn Ritualist",
    "Ghost of Ramirez DePietro"
  ],
  "Alharu, Solemn Ritualist / Gilanra, Caller of Wirewood": [
    "Alharu, Solemn Ritualist",
    "Gilanra, Caller of Wirewood"
  ],
  "Alharu, Solemn Ritualist / Glacian, Powerstone Engineer": [
    "Alharu, Solemn Ritualist",
    "Glacian, Powerstone Engineer"
  ],
  "Alharu, Solemn Ritualist / Halana, Kessig Ranger": [
    "Alharu, Solemn Ritualist",
    "Halana, Kessig Ranger"
  ],
  "Alharu, Solemn Ritualist / Ich-Tekik, Salvage Splicer": [
    "Alharu, Solemn Ritualist",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Alharu, Solemn Ritualist / Ikra Shidiqi, the Usurper": [
    "Alharu, Solemn Ritualist",
    "Ikra Shidiqi, the Usurper"
  ],
  "Alharu, Solemn Ritualist / Ishai, Ojutai Dragonspeaker": [
    "Alharu, Solemn Ritualist",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Alharu, Solemn Ritualist / Jeska, Thrice Reborn": [
    "Alharu, Solemn Ritualist",
    "Jeska, Thrice Reborn"
  ],
  "Alharu, Solemn Ritualist / Kamahl, Heart of Krosa": [
    "Alharu, Solemn Ritualist",
    "Kamahl, Heart of Krosa"
  ],
  "Alharu, Solemn Ritualist / Kediss, Emberclaw Familiar": [
    "Alharu, Solemn Ritualist",
    "Kediss, Emberclaw Familiar"
  ],
  "Alharu, Solemn Ritualist / Keleth, Sunmane Familiar": [
    "Alharu, Solemn Ritualist",
    "Keleth, Sunmane Familiar"
  ],
  "Alharu, Solemn Ritualist / Keskit, the Flesh Sculptor": [
    "Alharu, Solemn Ritualist",
    "Keskit, the Flesh Sculptor"
  ],
  "Alharu, Solemn Ritualist / Kodama of the East Tree": [
    "Alharu, Solemn Ritualist",
    "Kodama of the East Tree"
  ],
  "Alharu, Solemn Ritualist / Krark, the Thumbless": [
    "Alharu, Solemn Ritualist",
    "Krark, the Thumbless"
  ],
  "Alharu, Solemn Ritualist / Kraum, Ludevic's Opus": [
    "Alharu, Solemn Ritualist",
    "Kraum, Ludevic's Opus"
  ],
  "Alharu, Solemn Ritualist / Kydele, Chosen of Kruphix": [
    "Alharu, Solemn Ritualist",
    "Kydele, Chosen of Kruphix"
  ],
  "Alharu, Solemn Ritualist / Livio, Oathsworn Sentinel": [
    "Alharu, Solemn Ritualist",
    "Livio, Oathsworn Sentinel"
  ],
  "Alharu, Solemn Ritualist / Ludevic, Necro-Alchemist": [
    "Alharu, Solemn Ritualist",
    "Ludevic, Necro-Alchemist"
  ],
  "Alharu, Solemn Ritualist / Malcolm, Keen-Eyed Navigator": [
    "Alharu, Solemn Ritualist",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Alharu, Solemn Ritualist / Miara, Thorn of the Glade": [
    "Alharu, Solemn Ritualist",
    "Miara, Thorn of the Glade"
  ],
  "Alharu, Solemn Ritualist / Nadier, Agent of the Duskenel": [
    "Alharu, Solemn Ritualist",
    "Nadier, Agent of the Duskenel"
  ],
  "Alharu, Solemn Ritualist / Numa, Joraga Chieftain": [
    "Alharu, Solemn Ritualist",
    "Numa, Joraga Chieftain"
  ],
  "Alharu, Solemn Ritualist / Prava of the Steel Legion": [
    "Alharu, Solemn Ritualist",
    "Prava of the Steel Legion"
  ],
  "Alharu, Solemn Ritualist / Radiant, Serra Archangel": [
    "Alharu, Solemn Ritualist",
    "Radiant, Serra Archangel"
  ],
  "Alharu, Solemn Ritualist / Ravos, Soultender": [
    "Alharu, Solemn Ritualist",
    "Ravos, Soultender"
  ],
  "Alharu, Solemn Ritualist / Rebbec, Architect of Ascension": [
    "Alharu, Solemn Ritualist",
    "Rebbec, Architect of Ascension"
  ],
  "Alharu, Solemn Ritualist / Reyhan, Last of the Abzan": [
    "Alharu, Solemn Ritualist",
    "Reyhan, Last of the Abzan"
  ],
  "Alharu, Solemn Ritualist / Rograkh, Son of Rohgahh": [
    "Alharu, Solemn Ritualist",
    "Rograkh, Son of Rohgahh"
  ],
  "Alharu, Solemn Ritualist / Sakashima of a Thousand Faces": [
    "Alharu, Solemn Ritualist",
    "Sakashima of a Thousand Faces"
  ],
  "Alharu, Solemn Ritualist / Sengir, the Dark Baron": [
    "Alharu, Solemn Ritualist",
    "Sengir, the Dark Baron"
  ],
  "Alharu, Solemn Ritualist / Siani, Eye of the Storm": [
    "Alharu, Solemn Ritualist",
    "Siani, Eye of the Storm"
  ],
  "Alharu, Solemn Ritualist / Sidar Kondo of Jamuraa": [
    "Alharu, Solemn Ritualist",
    "Sidar Kondo of Jamuraa"
  ],
  "Alharu, Solemn Ritualist / Silas Renn, Seeker Adept": [
    "Alharu, Solemn Ritualist",
    "Silas Renn, Seeker Adept"
  ],
  "Alharu, Solemn Ritualist / Slurrk, All-Ingesting": [
    "Alharu, Solemn Ritualist",
    "Slurrk, All-Ingesting"
  ],
  "Alharu, Solemn Ritualist / Tana, the Bloodsower": [
    "Alharu, Solemn Ritualist",
    "Tana, the Bloodsower"
  ],
  "Alharu, Solemn Ritualist / Tevesh Szat, Doom of Fools": [
    "Alharu, Solemn Ritualist",
    "Tevesh Szat, Doom of Fools"
  ],
  "Alharu, Solemn Ritualist / The Prismatic Piper": [
    "Alharu, Solemn Ritualist",
    "The Prismatic Piper"
  ],
  "Alharu, Solemn Ritualist / Thrasios, Triton Hero": [
    "Alharu, Solemn Ritualist",
    "Thrasios, Triton Hero"
  ],
  "Alharu, Solemn Ritualist / Toggo, Goblin Weaponsmith": [
    "Alharu, Solemn Ritualist",
    "Toggo, Goblin Weaponsmith"
  ],
  "Alharu, Solemn Ritualist / Tormod, the Desecrator": [
    "Alharu, Solemn Ritualist",
    "Tormod, the Desecrator"
  ],
  "Alharu, Solemn Ritualist / Tymna the Weaver": [
    "Alharu, Solemn Ritualist",
    "Tymna the Weaver"
  ],
  "Alharu, Solemn Ritualist / Vial Smasher the Fierce": [
    "Alharu, Solemn Ritualist",
    "Vial Smasher the Fierce"
  ],
  "Alharu, Solemn Ritualist / Yoshimaru, Ever Faithful": [
    "Alharu, Solemn Ritualist",
    "Yoshimaru, Ever Faithful"
  ],
  "Alisaie Leveilleur / Alphinaud Leveilleur": [
    "Alisaie Leveilleur",
    "Alphinaud Leveilleur"
  ],
  "Alora, Merry Thief / Candlekeep Sage": [
    "Alora, Merry Thief",
    "Candlekeep Sage"
  ],
  "Alora, Merry Thief / Clan Crafter": [
    "Alora, Merry Thief",
    "Clan Crafter"
  ],
  "Alora, Merry Thief / Cloakwood Hermit": [
    "Alora, Merry Thief",
    "Cloakwood Hermit"
  ],
  "Alora, Merry Thief / Criminal Past": [
    "Alora, Merry Thief",
    "Criminal Past"
  ],
  "Alora, Merry Thief / Cultist of the Absolute": [
    "Alora, Merry Thief",
    "Cultist of the Absolute"
  ],
  "Alora, Merry Thief / Dragon Cultist": [
    "Alora, Merry Thief",
    "Dragon Cultist"
  ],
  "Alora, Merry Thief / Dungeon Delver": [
    "Alora, Merry Thief",
    "Dungeon Delver"
  ],
  "Alora, Merry Thief / Faceless One": [
    "Alora, Merry Thief",
    "Faceless One"
  ],
  "Alora, Merry Thief / Far Traveler": [
    "Alora, Merry Thief",
    "Far Traveler"
  ],
  "Alora, Merry Thief / Feywild Visitor": [
    "Alora, Merry Thief",
    "Feywild Visitor"
  ],
  "Alora, Merry Thief / Flaming Fist": [
    "Alora, Merry Thief",
    "Flaming Fist"
  ],
  "Alora, Merry Thief / Folk Hero": [
    "Alora, Merry Thief",
    "Folk Hero"
  ],
  "Alora, Merry Thief / Guild Artisan": [
    "Alora, Merry Thief",
    "Guild Artisan"
  ],
  "Alora, Merry Thief / Hardy Outlander": [
    "Alora, Merry Thief",
    "Hardy Outlander"
  ],
  "Alora, Merry Thief / Haunted One": [
    "Alora, Merry Thief",
    "Haunted One"
  ],
  "Alora, Merry Thief / Inspiring Leader": [
    "Alora, Merry Thief",
    "Inspiring Leader"
  ],
  "Alora, Merry Thief / Master Chef": [
    "Alora, Merry Thief",
    "Master Chef"
  ],
  "Alora, Merry Thief / Noble Heritage": [
    "Alora, Merry Thief",
    "Noble Heritage"
  ],
  "Alora, Merry Thief / Passionate Archaeologist": [
    "Alora, Merry Thief",
    "Passionate Archaeologist"
  ],
  "Alora, Merry Thief / Popular Entertainer": [
    "Alora, Merry Thief",
    "Popular Entertainer"
  ],
  "Alora, Merry Thief / Raised by Giants": [
    "Alora, Merry Thief",
    "Raised by Giants"
  ],
  "Alora, Merry Thief / Scion of Halaster": [
    "Alora, Merry Thief",
    "Scion of Halaster"
  ],
  "Alora, Merry Thief / Shameless Charlatan": [
    "Alora, Merry Thief",
    "Shameless Charlatan"
  ],
  "Alora, Merry Thief / Street Urchin": [
    "Alora, Merry Thief",
    "Street Urchin"
  ],
  "Alora, Merry Thief / Sword Coast Sailor": [
    "Alora, Merry Thief",
    "Sword Coast Sailor"
  ],
  "Alora, Merry Thief / Tavern Brawler": [
    "Alora, Merry Thief",
    "Tavern Brawler"
  ],
  "Alora, Merry Thief / Veteran Soldier": [
    "Alora, Merry Thief",
    "Veteran Soldier"
  ],
  "Amber Gristle O'Maul / Candlekeep Sage": [
    "Amber Gristle O'Maul",
    "Candlekeep Sage"
  ],
  "Amber Gristle O'Maul / Clan Crafter": [
    "Amber Gristle O'Maul",
    "Clan Crafter"
  ],
  "Amber Gristle O'Maul / Cloakwood Hermit": [
    "Amber Gristle O'Maul",
    "Cloakwood Hermit"
  ],
  "Amber Gristle O'Maul / Criminal Past": [
    "Amber Gristle O'Maul",
    "Criminal Past"
  ],
  "Amber Gristle O'Maul / Cultist of the Absolute": [
    "Amber Gristle O'Maul",
    "Cultist of the Absolute"
  ],
  "Amber Gristle O'Maul / Dragon Cultist": [
    "Amber Gristle O'Maul",
    "Dragon Cultist"
  ],
  "Amber Gristle O'Maul / Dungeon Delver": [
    "Amber Gristle O'Maul",
    "Dungeon Delver"
  ],
  "Amber Gristle O'Maul / Faceless One": [
    "Amber Gristle O'Maul",
    "Faceless One"
  ],
  "Amber Gristle O'Maul / Far Traveler": [
    "Amber Gristle O'Maul",
    "Far Traveler"
  ],
  "Amber Gristle O'Maul / Feywild Visitor": [
    "Amber Gristle O'Maul",
    "Feywild Visitor"
  ],
  "Amber Gristle O'Maul / Flaming Fist": [
    "Amber Gristle O'Maul",
    "Flaming Fist"
  ],
  "Amber Gristle O'Maul / Folk Hero": [
    "Amber Gristle O'Maul",
    "Folk Hero"
  ],
  "Amber Gristle O'Maul / Guild Artisan": [
    "Amber Gristle O'Maul",
    "Guild Artisan"
  ],
  "Amber Gristle O'Maul / Hardy Outlander": [
    "Amber Gristle O'Maul",
    "Hardy Outlander"
  ],
  "Amber Gristle O'Maul / Haunted One": [
    "Amber Gristle O'Maul",
    "Haunted One"
  ],
  "Amber Gristle O'Maul / Inspiring Leader": [
    "Amber Gristle O'Maul",
    "Inspiring Leader"
  ],
  "Amber Gristle O'Maul / Master Chef": [
    "Amber Gristle O'Maul",
    "Master Chef"
  ],
  "Amber Gristle O'Maul / Noble Heritage": [
    "Amber Gristle O'Maul",
    "Noble Heritage"
  ],
  "Amber Gristle O'Maul / Passionate Archaeologist": [
    "Amber Gristle O'Maul",
    "Passionate Archaeologist"
  ],
  "Amber Gristle O'Maul / Popular Entertainer": [
    "Amber Gristle O'Maul",
    "Popular Entertainer"
  ],
  "Amber Gristle O'Maul / Raised by Giants": [
    "Amber Gristle O'Maul",
    "Raised by Giants"
  ],
  "Amber Gristle O'Maul / Scion of Halaster": [
    "Amber Gristle O'Maul",
    "Scion of Halaster"
  ],
  "Amber Gristle O'Maul / Shameless Charlatan": [
    "Amber Gristle O'Maul",
    "Shameless Charlatan"
  ],
  "Amber Gristle O'Maul / Street Urchin": [
    "Amber Gristle O'Maul",
    "Street Urchin"
  ],
  "Amber Gristle O'Maul / Sword Coast Sailor": [
    "Amber Gristle O'Maul",
    "Sword Coast Sailor"
  ],
  "Amber Gristle O'Maul / Tavern Brawler": [
    "Amber Gristle O'Maul",
    "Tavern Brawler"
  ],
  "Amber Gristle O'Maul / Veteran Soldier": [
    "Amber Gristle O'Maul",
    "Veteran Soldier"
  ],
  "Amy Pond / Rory Williams": [
    "Amy Pond",
    "Rory Williams"
  ],
  "Amy Pond / The Eighth Doctor": [
    "Amy Pond",
    "The Eighth Doctor"
  ],
  "Amy Pond / The Eleventh Doctor": [
    "Amy Pond",
    "The Eleventh Doctor"
  ],
  "Amy Pond / The Fifteenth Doctor": [
    "Amy Pond",
    "The Fifteenth Doctor"
  ],
  "Amy Pond / The Fifth Doctor": [
    "Amy Pond",
    "The Fifth Doctor"
  ],
  "Amy Pond / The First Doctor": [
    "Amy Pond",
    "The First Doctor"
  ],
  "Amy Pond / The Fourteenth Doctor": [
    "Amy Pond",
    "The Fourteenth Doctor"
  ],
  "Amy Pond / The Fourth Doctor": [
    "Amy Pond",
    "The Fourth Doctor"
  ],
  "Amy Pond / The Fugitive Doctor": [
    "Amy Pond",
    "The Fugitive Doctor"
  ],
  "Amy Pond / The Ninth Doctor": [
    "Amy Pond",
    "The Ninth Doctor"
  ],
  "Amy Pond / The Second Doctor": [
    "Amy Pond",
    "The Second Doctor"
  ],
  "Amy Pond / The Seventh Doctor": [
    "Amy Pond",
    "The Seventh Doctor"
  ],
  "Amy Pond / The Sixth Doctor": [
    "Amy Pond",
    "The Sixth Doctor"
  ],
  "Amy Pond / The Tenth Doctor": [
    "Amy Pond",
    "The Tenth Doctor"
  ],
  "Amy Pond / The Third Doctor": [
    "Amy Pond",
    "The Third Doctor"
  ],
  "Amy Pond / The Thirteenth Doctor": [
    "Amy Pond",
    "The Thirteenth Doctor"
  ],
  "Amy Pond / The Twelfth Doctor": [
    "Amy Pond",
    "The Twelfth Doctor"
  ],
  "Amy Pond / The War Doctor": [
    "Amy Pond",
    "The War Doctor"
  ],
  "Anara, Wolvid Familiar / Ardenn, Intrepid Archaeologist": [
    "Anara, Wolvid Familiar",
    "Ardenn, Intrepid Archaeologist"
  ],
  "Anara, Wolvid Familiar / Armix, Filigree Thrasher": [
    "Anara, Wolvid Familiar",
    "Armix, Filigree Thrasher"
  ],
  "Anara, Wolvid Familiar / Breeches, Brazen Plunderer": [
    "Anara, Wolvid Familiar",
    "Breeches, Brazen Plunderer"
  ],
  "Anara, Wolvid Familiar / Brinelin, the Moon Kraken": [
    "Anara, Wolvid Familiar",
    "Brinelin, the Moon Kraken"
  ],
  "Anara, Wolvid Familiar / Bruse Tarl, Boorish Herder": [
    "Anara, Wolvid Familiar",
    "Bruse Tarl, Boorish Herder"
  ],
  "Anara, Wolvid Familiar / Dargo, the Shipwrecker": [
    "Anara, Wolvid Familiar",
    "Dargo, the Shipwrecker"
  ],
  "Anara, Wolvid Familiar / Eligeth, Crossroads Augur": [
    "Anara, Wolvid Familiar",
    "Eligeth, Crossroads Augur"
  ],
  "Anara, Wolvid Familiar / Esior, Wardwing Familiar": [
    "Anara, Wolvid Familiar",
    "Esior, Wardwing Familiar"
  ],
  "Anara, Wolvid Familiar / Falthis, Shadowcat Familiar": [
    "Anara, Wolvid Familiar",
    "Falthis, Shadowcat Familiar"
  ],
  "Anara, Wolvid Familiar / Francisco, Fowl Marauder": [
    "Anara, Wolvid Familiar",
    "Francisco, Fowl Marauder"
  ],
  "Anara, Wolvid Familiar / Ghost of Ramirez DePietro": [
    "Anara, Wolvid Familiar",
    "Ghost of Ramirez DePietro"
  ],
  "Anara, Wolvid Familiar / Gilanra, Caller of Wirewood": [
    "Anara, Wolvid Familiar",
    "Gilanra, Caller of Wirewood"
  ],
  "Anara, Wolvid Familiar / Glacian, Powerstone Engineer": [
    "Anara, Wolvid Familiar",
    "Glacian, Powerstone Engineer"
  ],
  "Anara, Wolvid Familiar / Halana, Kessig Ranger": [
    "Anara, Wolvid Familiar",
    "Halana, Kessig Ranger"
  ],
  "Anara, Wolvid Familiar / Ich-Tekik, Salvage Splicer": [
    "Anara, Wolvid Familiar",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Anara, Wolvid Familiar / Ikra Shidiqi, the Usurper": [
    "Anara, Wolvid Familiar",
    "Ikra Shidiqi, the Usurper"
  ],
  "Anara, Wolvid Familiar / Ishai, Ojutai Dragonspeaker": [
    "Anara, Wolvid Familiar",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Anara, Wolvid Familiar / Jeska, Thrice Reborn": [
    "Anara, Wolvid Familiar",
    "Jeska, Thrice Reborn"
  ],
  "Anara, Wolvid Familiar / Kamahl, Heart of Krosa": [
    "Anara, Wolvid Familiar",
    "Kamahl, Heart of Krosa"
  ],
  "Anara, Wolvid Familiar / Kediss, Emberclaw Familiar": [
    "Anara, Wolvid Familiar",
    "Kediss, Emberclaw Familiar"
  ],
  "Anara, Wolvid Familiar / Keleth, Sunmane Familiar": [
    "Anara, Wolvid Familiar",
    "Keleth, Sunmane Familiar"
  ],
  "Anara, Wolvid Familiar / Keskit, the Flesh Sculptor": [
    "Anara, Wolvid Familiar",
    "Keskit, the Flesh Sculptor"
  ],
  "Anara, Wolvid Familiar / Kodama of the East Tree": [
    "Anara, Wolvid Familiar",
    "Kodama of the East Tree"
  ],
  "Anara, Wolvid Familiar / Krark, the Thumbless": [
    "Anara, Wolvid Familiar",
    "Krark, the Thumbless"
  ],
  "Anara, Wolvid Familiar / Kraum, Ludevic's Opus": [
    "Anara, Wolvid Familiar",
    "Kraum, Ludevic's Opus"
  ],
  "Anara, Wolvid Familiar / Kydele, Chosen of Kruphix": [
    "Anara, Wolvid Familiar",
    "Kydele, Chosen of Kruphix"
  ],
  "Anara, Wolvid Familiar / Livio, Oathsworn Sentinel": [
    "Anara, Wolvid Familiar",
    "Livio, Oathsworn Sentinel"
  ],
  "Anara, Wolvid Familiar / Ludevic, Necro-Alchemist": [
    "Anara, Wolvid Familiar",
    "Ludevic, Necro-Alchemist"
  ],
  "Anara, Wolvid Familiar / Malcolm, Keen-Eyed Navigator": [
    "Anara, Wolvid Familiar",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Anara, Wolvid Familiar / Miara, Thorn of the Glade": [
    "Anara, Wolvid Familiar",
    "Miara, Thorn of the Glade"
  ],
  "Anara, Wolvid Familiar / Nadier, Agent of the Duskenel": [
    "Anara, Wolvid Familiar",
    "Nadier, Agent of the Duskenel"
  ],
  "Anara, Wolvid Familiar / Numa, Joraga Chieftain": [
    "Anara, Wolvid Familiar",
    "Numa, Joraga Chieftain"
  ],
  "Anara, Wolvid Familiar / Prava of the Steel Legion": [
    "Anara, Wolvid Familiar",
    "Prava of the Steel Legion"
  ],
  "Anara, Wolvid Familiar / Radiant, Serra Archangel": [
    "Anara, Wolvid Familiar",
    "Radiant, Serra Archangel"
  ],
  "Anara, Wolvid Familiar / Ravos, Soultender": [
    "Anara, Wolvid Familiar",
    "Ravos, Soultender"
  ],
  "Anara, Wolvid Familiar / Rebbec, Architect of Ascension": [
    "Anara, Wolvid Familiar",
    "Rebbec, Architect of Ascension"
  ],
  "Anara, Wolvid Familiar / Reyhan, Last of the Abzan": [
    "Anara, Wolvid Familiar",
    "Reyhan, Last of the Abzan"
  ],
  "Anara, Wolvid Familiar / Rograkh, Son of Rohgahh": [
    "Anara, Wolvid Familiar",
    "Rograkh, Son of Rohgahh"
  ],
  "Anara, Wolvid Familiar / Sakashima of a Thousand Faces": [
    "Anara, Wolvid Familiar",
    "Sakashima of a Thousand Faces"
  ],
  "Anara, Wolvid Familiar / Sengir, the Dark Baron": [
    "Anara, Wolvid Familiar",
    "Sengir, the Dark Baron"
  ],
  "Anara, Wolvid Familiar / Siani, Eye of the Storm": [
    "Anara, Wolvid Familiar",
    "Siani, Eye of the Storm"
  ],
  "Anara, Wolvid Familiar / Sidar Kondo of Jamuraa": [
    "Anara, Wolvid Familiar",
    "Sidar Kondo of Jamuraa"
  ],
  "Anara, Wolvid Familiar / Silas Renn, Seeker Adept": [
    "Anara, Wolvid Familiar",
    "Silas Renn, Seeker Adept"
  ],
  "Anara, Wolvid Familiar / Slurrk, All-Ingesting": [
    "Anara, Wolvid Familiar",
    "Slurrk, All-Ingesting"
  ],
  "Anara, Wolvid Familiar / Tana, the Bloodsower": [
    "Anara, Wolvid Familiar",
    "Tana, the Bloodsower"
  ],
  "Anara, Wolvid Familiar / Tevesh Szat, Doom of Fools": [
    "Anara, Wolvid Familiar",
    "Tevesh Szat, Doom of Fools"
  ],
  "Anara, Wolvid Familiar / The Prismatic Piper": [
    "Anara, Wolvid Familiar",
    "The Prismatic Piper"
  ],
  "Anara, Wolvid Familiar / Thrasios, Triton Hero": [
    "Anara, Wolvid Familiar",
    "Thrasios, Triton Hero"
  ],
  "Anara, Wolvid Familiar / Toggo, Goblin Weaponsmith": [
    "Anara, Wolvid Familiar",
    "Toggo, Goblin Weaponsmith"
  ],
  "Anara, Wolvid Familiar / Tormod, the Desecrator": [
    "Anara, Wolvid Familiar",
    "Tormod, the Desecrator"
  ],
  "Anara, Wolvid Familiar / Tymna the Weaver": [
    "Anara, Wolvid Familiar",
    "Tymna the Weaver"
  ],
  "Anara, Wolvid Familiar / Vial Smasher the Fierce": [
    "Anara, Wolvid Familiar",
    "Vial Smasher the Fierce"
  ],
  "Anara, Wolvid Familiar / Yoshimaru, Ever Faithful": [
    "Anara, Wolvid Familiar",
    "Yoshimaru, Ever Faithful"
  ],
  "April O'Neil, Live on the Scene / Donatello, the Brains": [
    "April O'Neil, Live on the Scene",
    "Donatello, the Brains"
  ],
  "April O'Neil, Live on the Scene / Leonardo, the Balance": [
    "April O'Neil, Live on the Scene",
    "Leonardo, the Balance"
  ],
  "April O'Neil, Live on the Scene / Michelangelo, the Heart": [
    "April O'Neil, Live on the Scene",
    "Michelangelo, the Heart"
  ],
  "April O'Neil, Live on the Scene / Raphael, the Muscle": [
    "April O'Neil, Live on the Scene",
    "Raphael, the Muscle"
  ],
  "April O'Neil, Live on the Scene / Splinter, the Mentor": [
    "April O'Neil, Live on the Scene",
    "Splinter, the Mentor"
  ],
  "Ardenn, Intrepid Archaeologist / Armix, Filigree Thrasher": [
    "Ardenn, Intrepid Archaeologist",
    "Armix, Filigree Thrasher"
  ],
  "Ardenn, Intrepid Archaeologist / Breeches, Brazen Plunderer": [
    "Ardenn, Intrepid Archaeologist",
    "Breeches, Brazen Plunderer"
  ],
  "Ardenn, Intrepid Archaeologist / Brinelin, the Moon Kraken": [
    "Ardenn, Intrepid Archaeologist",
    "Brinelin, the Moon Kraken"
  ],
  "Ardenn, Intrepid Archaeologist / Bruse Tarl, Boorish Herder": [
    "Ardenn, Intrepid Archaeologist",
    "Bruse Tarl, Boorish Herder"
  ],
  "Ardenn, Intrepid Archaeologist / Dargo, the Shipwrecker": [
    "Ardenn, Intrepid Archaeologist",
    "Dargo, the Shipwrecker"
  ],
  "Ardenn, Intrepid Archaeologist / Eligeth, Crossroads Augur": [
    "Ardenn, Intrepid Archaeologist",
    "Eligeth, Crossroads Augur"
  ],
  "Ardenn, Intrepid Archaeologist / Esior, Wardwing Familiar": [
    "Ardenn, Intrepid Archaeologist",
    "Esior, Wardwing Familiar"
  ],
  "Ardenn, Intrepid Archaeologist / Falthis, Shadowcat Familiar": [
    "Ardenn, Intrepid Archaeologist",
    "Falthis, Shadowcat Familiar"
  ],
  "Ardenn, Intrepid Archaeologist / Francisco, Fowl Marauder": [
    "Ardenn, Intrepid Archaeologist",
    "Francisco, Fowl Marauder"
  ],
  "Ardenn, Intrepid Archaeologist / Ghost of Ramirez DePietro": [
    "Ardenn, Intrepid Archaeologist",
    "Ghost of Ramirez DePietro"
  ],
  "Ardenn, Intrepid Archaeologist / Gilanra, Caller of Wirewood": [
    "Ardenn, Intrepid Archaeologist",
    "Gilanra, Caller of Wirewood"
  ],
  "Ardenn, Intrepid Archaeologist / Glacian, Powerstone Engineer": [
    "Ardenn, Intrepid Archaeologist",
    "Glacian, Powerstone Engineer"
  ],
  "Ardenn, Intrepid Archaeologist / Halana, Kessig Ranger": [
    "Ardenn, Intrepid Archaeologist",
    "Halana, Kessig Ranger"
  ],
  "Ardenn, Intrepid Archaeologist / Ich-Tekik, Salvage Splicer": [
    "Ardenn, Intrepid Archaeologist",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Ardenn, Intrepid Archaeologist / Ikra Shidiqi, the Usurper": [
    "Ardenn, Intrepid Archaeologist",
    "Ikra Shidiqi, the Usurper"
  ],
  "Ardenn, Intrepid Archaeologist / Ishai, Ojutai Dragonspeaker": [
    "Ardenn, Intrepid Archaeologist",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ardenn, Intrepid Archaeologist / Jeska, Thrice Reborn": [
    "Ardenn, Intrepid Archaeologist",
    "Jeska, Thrice Reborn"
  ],
  "Ardenn, Intrepid Archaeologist / Kamahl, Heart of Krosa": [
    "Ardenn, Intrepid Archaeologist",
    "Kamahl, Heart of Krosa"
  ],
  "Ardenn, Intrepid Archaeologist / Kediss, Emberclaw Familiar": [
    "Ardenn, Intrepid Archaeologist",
    "Kediss, Emberclaw Familiar"
  ],
  "Ardenn, Intrepid Archaeologist / Keleth, Sunmane Familiar": [
    "Ardenn, Intrepid Archaeologist",
    "Keleth, Sunmane Familiar"
  ],
  "Ardenn, Intrepid Archaeologist / Keskit, the Flesh Sculptor": [
    "Ardenn, Intrepid Archaeologist",
    "Keskit, the Flesh Sculptor"
  ],
  "Ardenn, Intrepid Archaeologist / Kodama of the East Tree": [
    "Ardenn, Intrepid Archaeologist",
    "Kodama of the East Tree"
  ],
  "Ardenn, Intrepid Archaeologist / Krark, the Thumbless": [
    "Ardenn, Intrepid Archaeologist",
    "Krark, the Thumbless"
  ],
  "Ardenn, Intrepid Archaeologist / Kraum, Ludevic's Opus": [
    "Ardenn, Intrepid Archaeologist",
    "Kraum, Ludevic's Opus"
  ],
  "Ardenn, Intrepid Archaeologist / Kydele, Chosen of Kruphix": [
    "Ardenn, Intrepid Archaeologist",
    "Kydele, Chosen of Kruphix"
  ],
  "Ardenn, Intrepid Archaeologist / Livio, Oathsworn Sentinel": [
    "Ardenn, Intrepid Archaeologist",
    "Livio, Oathsworn Sentinel"
  ],
  "Ardenn, Intrepid Archaeologist / Ludevic, Necro-Alchemist": [
    "Ardenn, Intrepid Archaeologist",
    "Ludevic, Necro-Alchemist"
  ],
  "Ardenn, Intrepid Archaeologist / Malcolm, Keen-Eyed Navigator": [
    "Ardenn, Intrepid Archaeologist",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ardenn, Intrepid Archaeologist / Miara, Thorn of the Glade": [
    "Ardenn, Intrepid Archaeologist",
    "Miara, Thorn of the Glade"
  ],
  "Ardenn, Intrepid Archaeologist / Nadier, Agent of the Duskenel": [
    "Ardenn, Intrepid Archaeologist",
    "Nadier, Agent of the Duskenel"
  ],
  "Ardenn, Intrepid Archaeologist / Numa, Joraga Chieftain": [
    "Ardenn, Intrepid Archaeologist",
    "Numa, Joraga Chieftain"
  ],
  "Ardenn, Intrepid Archaeologist / Prava of the Steel Legion": [
    "Ardenn, Intrepid Archaeologist",
    "Prava of the Steel Legion"
  ],
  "Ardenn, Intrepid Archaeologist / Radiant, Serra Archangel": [
    "Ardenn, Intrepid Archaeologist",
    "Radiant, Serra Archangel"
  ],
  "Ardenn, Intrepid Archaeologist / Ravos, Soultender": [
    "Ardenn, Intrepid Archaeologist",
    "Ravos, Soultender"
  ],
  "Ardenn, Intrepid Archaeologist / Rebbec, Architect of Ascension": [
    "Ardenn, Intrepid Archaeologist",
    "Rebbec, Architect of Ascension"
  ],
  "Ardenn, Intrepid Archaeologist / Reyhan, Last of the Abzan": [
    "Ardenn, Intrepid Archaeologist",
    "Reyhan, Last of the Abzan"
  ],
  "Ardenn, Intrepid Archaeologist / Rograkh, Son of Rohgahh": [
    "Ardenn, Intrepid Archaeologist",
    "Rograkh, Son of Rohgahh"
  ],
  "Ardenn, Intrepid Archaeologist / Sakashima of a Thousand Faces": [
    "Ardenn, Intrepid Archaeologist",
    "Sakashima of a Thousand Faces"
  ],
  "Ardenn, Intrepid Archaeologist / Sengir, the Dark Baron": [
    "Ardenn, Intrepid Archaeologist",
    "Sengir, the Dark Baron"
  ],
  "Ardenn, Intrepid Archaeologist / Siani, Eye of the Storm": [
    "Ardenn, Intrepid Archaeologist",
    "Siani, Eye of the Storm"
  ],
  "Ardenn, Intrepid Archaeologist / Sidar Kondo of Jamuraa": [
    "Ardenn, Intrepid Archaeologist",
    "Sidar Kondo of Jamuraa"
  ],
  "Ardenn, Intrepid Archaeologist / Silas Renn, Seeker Adept": [
    "Ardenn, Intrepid Archaeologist",
    "Silas Renn, Seeker Adept"
  ],
  "Ardenn, Intrepid Archaeologist / Slurrk, All-Ingesting": [
    "Ardenn, Intrepid Archaeologist",
    "Slurrk, All-Ingesting"
  ],
  "Ardenn, Intrepid Archaeologist / Tana, the Bloodsower": [
    "Ardenn, Intrepid Archaeologist",
    "Tana, the Bloodsower"
  ],
  "Ardenn, Intrepid Archaeologist / Tevesh Szat, Doom of Fools": [
    "Ardenn, Intrepid Archaeologist",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ardenn, Intrepid Archaeologist / The Prismatic Piper": [
    "Ardenn, Intrepid Archaeologist",
    "The Prismatic Piper"
  ],
  "Ardenn, Intrepid Archaeologist / Thrasios, Triton Hero": [
    "Ardenn, Intrepid Archaeologist",
    "Thrasios, Triton Hero"
  ],
  "Ardenn, Intrepid Archaeologist / Toggo, Goblin Weaponsmith": [
    "Ardenn, Intrepid Archaeologist",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ardenn, Intrepid Archaeologist / Tormod, the Desecrator": [
    "Ardenn, Intrepid Archaeologist",
    "Tormod, the Desecrator"
  ],
  "Ardenn, Intrepid Archaeologist / Tymna the Weaver": [
    "Ardenn, Intrepid Archaeologist",
    "Tymna the Weaver"
  ],
  "Ardenn, Intrepid Archaeologist / Vial Smasher the Fierce": [
    "Ardenn, Intrepid Archaeologist",
    "Vial Smasher the Fierce"
  ],
  "Ardenn, Intrepid Archaeologist / Yoshimaru, Ever Faithful": [
    "Ardenn, Intrepid Archaeologist",
    "Yoshimaru, Ever Faithful"
  ],
  "Armix, Filigree Thrasher / Breeches, Brazen Plunderer": [
    "Armix, Filigree Thrasher",
    "Breeches, Brazen Plunderer"
  ],
  "Armix, Filigree Thrasher / Brinelin, the Moon Kraken": [
    "Armix, Filigree Thrasher",
    "Brinelin, the Moon Kraken"
  ],
  "Armix, Filigree Thrasher / Bruse Tarl, Boorish Herder": [
    "Armix, Filigree Thrasher",
    "Bruse Tarl, Boorish Herder"
  ],
  "Armix, Filigree Thrasher / Dargo, the Shipwrecker": [
    "Armix, Filigree Thrasher",
    "Dargo, the Shipwrecker"
  ],
  "Armix, Filigree Thrasher / Eligeth, Crossroads Augur": [
    "Armix, Filigree Thrasher",
    "Eligeth, Crossroads Augur"
  ],
  "Armix, Filigree Thrasher / Esior, Wardwing Familiar": [
    "Armix, Filigree Thrasher",
    "Esior, Wardwing Familiar"
  ],
  "Armix, Filigree Thrasher / Falthis, Shadowcat Familiar": [
    "Armix, Filigree Thrasher",
    "Falthis, Shadowcat Familiar"
  ],
  "Armix, Filigree Thrasher / Francisco, Fowl Marauder": [
    "Armix, Filigree Thrasher",
    "Francisco, Fowl Marauder"
  ],
  "Armix, Filigree Thrasher / Ghost of Ramirez DePietro": [
    "Armix, Filigree Thrasher",
    "Ghost of Ramirez DePietro"
  ],
  "Armix, Filigree Thrasher / Gilanra, Caller of Wirewood": [
    "Armix, Filigree Thrasher",
    "Gilanra, Caller of Wirewood"
  ],
  "Armix, Filigree Thrasher / Glacian, Powerstone Engineer": [
    "Armix, Filigree Thrasher",
    "Glacian, Powerstone Engineer"
  ],
  "Armix, Filigree Thrasher / Halana, Kessig Ranger": [
    "Armix, Filigree Thrasher",
    "Halana, Kessig Ranger"
  ],
  "Armix, Filigree Thrasher / Ich-Tekik, Salvage Splicer": [
    "Armix, Filigree Thrasher",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Armix, Filigree Thrasher / Ikra Shidiqi, the Usurper": [
    "Armix, Filigree Thrasher",
    "Ikra Shidiqi, the Usurper"
  ],
  "Armix, Filigree Thrasher / Ishai, Ojutai Dragonspeaker": [
    "Armix, Filigree Thrasher",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Armix, Filigree Thrasher / Jeska, Thrice Reborn": [
    "Armix, Filigree Thrasher",
    "Jeska, Thrice Reborn"
  ],
  "Armix, Filigree Thrasher / Kamahl, Heart of Krosa": [
    "Armix, Filigree Thrasher",
    "Kamahl, Heart of Krosa"
  ],
  "Armix, Filigree Thrasher / Kediss, Emberclaw Familiar": [
    "Armix, Filigree Thrasher",
    "Kediss, Emberclaw Familiar"
  ],
  "Armix, Filigree Thrasher / Keleth, Sunmane Familiar": [
    "Armix, Filigree Thrasher",
    "Keleth, Sunmane Familiar"
  ],
  "Armix, Filigree Thrasher / Keskit, the Flesh Sculptor": [
    "Armix, Filigree Thrasher",
    "Keskit, the Flesh Sculptor"
  ],
  "Armix, Filigree Thrasher / Kodama of the East Tree": [
    "Armix, Filigree Thrasher",
    "Kodama of the East Tree"
  ],
  "Armix, Filigree Thrasher / Krark, the Thumbless": [
    "Armix, Filigree Thrasher",
    "Krark, the Thumbless"
  ],
  "Armix, Filigree Thrasher / Kraum, Ludevic's Opus": [
    "Armix, Filigree Thrasher",
    "Kraum, Ludevic's Opus"
  ],
  "Armix, Filigree Thrasher / Kydele, Chosen of Kruphix": [
    "Armix, Filigree Thrasher",
    "Kydele, Chosen of Kruphix"
  ],
  "Armix, Filigree Thrasher / Livio, Oathsworn Sentinel": [
    "Armix, Filigree Thrasher",
    "Livio, Oathsworn Sentinel"
  ],
  "Armix, Filigree Thrasher / Ludevic, Necro-Alchemist": [
    "Armix, Filigree Thrasher",
    "Ludevic, Necro-Alchemist"
  ],
  "Armix, Filigree Thrasher / Malcolm, Keen-Eyed Navigator": [
    "Armix, Filigree Thrasher",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Armix, Filigree Thrasher / Miara, Thorn of the Glade": [
    "Armix, Filigree Thrasher",
    "Miara, Thorn of the Glade"
  ],
  "Armix, Filigree Thrasher / Nadier, Agent of the Duskenel": [
    "Armix, Filigree Thrasher",
    "Nadier, Agent of the Duskenel"
  ],
  "Armix, Filigree Thrasher / Numa, Joraga Chieftain": [
    "Armix, Filigree Thrasher",
    "Numa, Joraga Chieftain"
  ],
  "Armix, Filigree Thrasher / Prava of the Steel Legion": [
    "Armix, Filigree Thrasher",
    "Prava of the Steel Legion"
  ],
  "Armix, Filigree Thrasher / Radiant, Serra Archangel": [
    "Armix, Filigree Thrasher",
    "Radiant, Serra Archangel"
  ],
  "Armix, Filigree Thrasher / Ravos, Soultender": [
    "Armix, Filigree Thrasher",
    "Ravos, Soultender"
  ],
  "Armix, Filigree Thrasher / Rebbec, Architect of Ascension": [
    "Armix, Filigree Thrasher",
    "Rebbec, Architect of Ascension"
  ],
  "Armix, Filigree Thrasher / Reyhan, Last of the Abzan": [
    "Armix, Filigree Thrasher",
    "Reyhan, Last of the Abzan"
  ],
  "Armix, Filigree Thrasher / Rograkh, Son of Rohgahh": [
    "Armix, Filigree Thrasher",
    "Rograkh, Son of Rohgahh"
  ],
  "Armix, Filigree Thrasher / Sakashima of a Thousand Faces": [
    "Armix, Filigree Thrasher",
    "Sakashima of a Thousand Faces"
  ],
  "Armix, Filigree Thrasher / Sengir, the Dark Baron": [
    "Armix, Filigree Thrasher",
    "Sengir, the Dark Baron"
  ],
  "Armix, Filigree Thrasher / Siani, Eye of the Storm": [
    "Armix, Filigree Thrasher",
    "Siani, Eye of the Storm"
  ],
  "Armix, Filigree Thrasher / Sidar Kondo of Jamuraa": [
    "Armix, Filigree Thrasher",
    "Sidar Kondo of Jamuraa"
  ],
  "Armix, Filigree Thrasher / Silas Renn, Seeker Adept": [
    "Armix, Filigree Thrasher",
    "Silas Renn, Seeker Adept"
  ],
  "Armix, Filigree Thrasher / Slurrk, All-Ingesting": [
    "Armix, Filigree Thrasher",
    "Slurrk, All-Ingesting"
  ],
  "Armix, Filigree Thrasher / Tana, the Bloodsower": [
    "Armix, Filigree Thrasher",
    "Tana, the Bloodsower"
  ],
  "Armix, Filigree Thrasher / Tevesh Szat, Doom of Fools": [
    "Armix, Filigree Thrasher",
    "Tevesh Szat, Doom of Fools"
  ],
  "Armix, Filigree Thrasher / The Prismatic Piper": [
    "Armix, Filigree Thrasher",
    "The Prismatic Piper"
  ],
  "Armix, Filigree Thrasher / Thrasios, Triton Hero": [
    "Armix, Filigree Thrasher",
    "Thrasios, Triton Hero"
  ],
  "Armix, Filigree Thrasher / Toggo, Goblin Weaponsmith": [
    "Armix, Filigree Thrasher",
    "Toggo, Goblin Weaponsmith"
  ],
  "Armix, Filigree Thrasher / Tormod, the Desecrator": [
    "Armix, Filigree Thrasher",
    "Tormod, the Desecrator"
  ],
  "Armix, Filigree Thrasher / Tymna the Weaver": [
    "Armix, Filigree Thrasher",
    "Tymna the Weaver"
  ],
  "Armix, Filigree Thrasher / Vial Smasher the Fierce": [
    "Armix, Filigree Thrasher",
    "Vial Smasher the Fierce"
  ],
  "Armix, Filigree Thrasher / Yoshimaru, Ever Faithful": [
    "Armix, Filigree Thrasher",
    "Yoshimaru, Ever Faithful"
  ],
  "Atreus, Impulsive Son / Kratos, Stoic Father": [
    "Atreus, Impulsive Son",
    "Kratos, Stoic Father"
  ],
  "Baeloth Barrityl, Entertainer / Candlekeep Sage": [
    "Baeloth Barrityl, Entertainer",
    "Candlekeep Sage"
  ],
  "Baeloth Barrityl, Entertainer / Clan Crafter": [
    "Baeloth Barrityl, Entertainer",
    "Clan Crafter"
  ],
  "Baeloth Barrityl, Entertainer / Cloakwood Hermit": [
    "Baeloth Barrityl, Entertainer",
    "Cloakwood Hermit"
  ],
  "Baeloth Barrityl, Entertainer / Criminal Past": [
    "Baeloth Barrityl, Entertainer",
    "Criminal Past"
  ],
  "Baeloth Barrityl, Entertainer / Cultist of the Absolute": [
    "Baeloth Barrityl, Entertainer",
    "Cultist of the Absolute"
  ],
  "Baeloth Barrityl, Entertainer / Dragon Cultist": [
    "Baeloth Barrityl, Entertainer",
    "Dragon Cultist"
  ],
  "Baeloth Barrityl, Entertainer / Dungeon Delver": [
    "Baeloth Barrityl, Entertainer",
    "Dungeon Delver"
  ],
  "Baeloth Barrityl, Entertainer / Faceless One": [
    "Baeloth Barrityl, Entertainer",
    "Faceless One"
  ],
  "Baeloth Barrityl, Entertainer / Far Traveler": [
    "Baeloth Barrityl, Entertainer",
    "Far Traveler"
  ],
  "Baeloth Barrityl, Entertainer / Feywild Visitor": [
    "Baeloth Barrityl, Entertainer",
    "Feywild Visitor"
  ],
  "Baeloth Barrityl, Entertainer / Flaming Fist": [
    "Baeloth Barrityl, Entertainer",
    "Flaming Fist"
  ],
  "Baeloth Barrityl, Entertainer / Folk Hero": [
    "Baeloth Barrityl, Entertainer",
    "Folk Hero"
  ],
  "Baeloth Barrityl, Entertainer / Guild Artisan": [
    "Baeloth Barrityl, Entertainer",
    "Guild Artisan"
  ],
  "Baeloth Barrityl, Entertainer / Hardy Outlander": [
    "Baeloth Barrityl, Entertainer",
    "Hardy Outlander"
  ],
  "Baeloth Barrityl, Entertainer / Haunted One": [
    "Baeloth Barrityl, Entertainer",
    "Haunted One"
  ],
  "Baeloth Barrityl, Entertainer / Inspiring Leader": [
    "Baeloth Barrityl, Entertainer",
    "Inspiring Leader"
  ],
  "Baeloth Barrityl, Entertainer / Master Chef": [
    "Baeloth Barrityl, Entertainer",
    "Master Chef"
  ],
  "Baeloth Barrityl, Entertainer / Noble Heritage": [
    "Baeloth Barrityl, Entertainer",
    "Noble Heritage"
  ],
  "Baeloth Barrityl, Entertainer / Passionate Archaeologist": [
    "Baeloth Barrityl, Entertainer",
    "Passionate Archaeologist"
  ],
  "Baeloth Barrityl, Entertainer / Popular Entertainer": [
    "Baeloth Barrityl, Entertainer",
    "Popular Entertainer"
  ],
  "Baeloth Barrityl, Entertainer / Raised by Giants": [
    "Baeloth Barrityl, Entertainer",
    "Raised by Giants"
  ],
  "Baeloth Barrityl, Entertainer / Scion of Halaster": [
    "Baeloth Barrityl, Entertainer",
    "Scion of Halaster"
  ],
  "Baeloth Barrityl, Entertainer / Shameless Charlatan": [
    "Baeloth Barrityl, Entertainer",
    "Shameless Charlatan"
  ],
  "Baeloth Barrityl, Entertainer / Street Urchin": [
    "Baeloth Barrityl, Entertainer",
    "Street Urchin"
  ],
  "Baeloth Barrityl, Entertainer / Sword Coast Sailor": [
    "Baeloth Barrityl, Entertainer",
    "Sword Coast Sailor"
  ],
  "Baeloth Barrityl, Entertainer / Tavern Brawler": [
    "Baeloth Barrityl, Entertainer",
    "Tavern Brawler"
  ],
  "Baeloth Barrityl, Entertainer / Veteran Soldier": [
    "Baeloth Barrityl, Entertainer",
    "Veteran Soldier"
  ],
  "Barbara Wright / The Eighth Doctor": [
    "Barbara Wright",
    "The Eighth Doctor"
  ],
  "Barbara Wright / The Eleventh Doctor": [
    "Barbara Wright",
    "The Eleventh Doctor"
  ],
  "Barbara Wright / The Fifteenth Doctor": [
    "Barbara Wright",
    "The Fifteenth Doctor"
  ],
  "Barbara Wright / The Fifth Doctor": [
    "Barbara Wright",
    "The Fifth Doctor"
  ],
  "Barbara Wright / The First Doctor": [
    "Barbara Wright",
    "The First Doctor"
  ],
  "Barbara Wright / The Fourteenth Doctor": [
    "Barbara Wright",
    "The Fourteenth Doctor"
  ],
  "Barbara Wright / The Fourth Doctor": [
    "Barbara Wright",
    "The Fourth Doctor"
  ],
  "Barbara Wright / The Fugitive Doctor": [
    "Barbara Wright",
    "The Fugitive Doctor"
  ],
  "Barbara Wright / The Ninth Doctor": [
    "Barbara Wright",
    "The Ninth Doctor"
  ],
  "Barbara Wright / The Second Doctor": [
    "Barbara Wright",
    "The Second Doctor"
  ],
  "Barbara Wright / The Seventh Doctor": [
    "Barbara Wright",
    "The Seventh Doctor"
  ],
  "Barbara Wright / The Sixth Doctor": [
    "Barbara Wright",
    "The Sixth Doctor"
  ],
  "Barbara Wright / The Tenth Doctor": [
    "Barbara Wright",
    "The Tenth Doctor"
  ],
  "Barbara Wright / The Third Doctor": [
    "Barbara Wright",
    "The Third Doctor"
  ],
  "Barbara Wright / The Thirteenth Doctor": [
    "Barbara Wright",
    "The Thirteenth Doctor"
  ],
  "Barbara Wright / The Twelfth Doctor": [
    "Barbara Wright",
    "The Twelfth Doctor"
  ],
  "Barbara Wright / The War Doctor": [
    "Barbara Wright",
    "The War Doctor"
  ],
  "Bebop, Skull & Crossbones / Rocksteady, Mutant Marauder": [
    "Bebop, Skull & Crossbones",
    "Rocksteady, Mutant Marauder"
  ],
  "Bill Potts / The Eighth Doctor": [
    "Bill Potts",
    "The Eighth Doctor"
  ],
  "Bill Potts / The Eleventh Doctor": [
    "Bill Potts",
    "The Eleventh Doctor"
  ],
  "Bill Potts / The Fifteenth Doctor": [
    "Bill Potts",
    "The Fifteenth Doctor"
  ],
  "Bill Potts / The Fifth Doctor": [
    "Bill Potts",
    "The Fifth Doctor"
  ],
  "Bill Potts / The First Doctor": [
    "Bill Potts",
    "The First Doctor"
  ],
  "Bill Potts / The Fourteenth Doctor": [
    "Bill Potts",
    "The Fourteenth Doctor"
  ],
  "Bill Potts / The Fourth Doctor": [
    "Bill Potts",
    "The Fourth Doctor"
  ],
  "Bill Potts / The Fugitive Doctor": [
    "Bill Potts",
    "The Fugitive Doctor"
  ],
  "Bill Potts / The Ninth Doctor": [
    "Bill Potts",
    "The Ninth Doctor"
  ],
  "Bill Potts / The Second Doctor": [
    "Bill Potts",
    "The Second Doctor"
  ],
  "Bill Potts / The Seventh Doctor": [
    "Bill Potts",
    "The Seventh Doctor"
  ],
  "Bill Potts / The Sixth Doctor": [
    "Bill Potts",
    "The Sixth Doctor"
  ],
  "Bill Potts / The Tenth Doctor": [
    "Bill Potts",
    "The Tenth Doctor"
  ],
  "Bill Potts / The Third Doctor": [
    "Bill Potts",
    "The Third Doctor"
  ],
  "Bill Potts / The Thirteenth Doctor": [
    "Bill Potts",
    "The Thirteenth Doctor"
  ],
  "Bill Potts / The Twelfth Doctor": [
    "Bill Potts",
    "The Twelfth Doctor"
  ],
  "Bill Potts / The War Doctor": [
    "Bill Potts",
    "The War Doctor"
  ],
  "Bjorna, Nightfall Alchemist / Cecily, Haunted Mage": [
    "Bjorna, Nightfall Alchemist",
    "Cecily, Haunted Mage"
  ],
  "Bjorna, Nightfall Alchemist / Elmar, Ulvenwald Informant": [
    "Bjorna, Nightfall Alchemist",
    "Elmar, Ulvenwald Informant"
  ],
  "Bjorna, Nightfall Alchemist / Hargilde, Kindly Runechanter": [
    "Bjorna, Nightfall Alchemist",
    "Hargilde, Kindly Runechanter"
  ],
  "Bjorna, Nightfall Alchemist / Othelm, Sigardian Outcast": [
    "Bjorna, Nightfall Alchemist",
    "Othelm, Sigardian Outcast"
  ],
  "Bjorna, Nightfall Alchemist / Sophina, Spearsage Deserter": [
    "Bjorna, Nightfall Alchemist",
    "Sophina, Spearsage Deserter"
  ],
  "Bjorna, Nightfall Alchemist / Wernog, Rider's Chaplain": [
    "Bjorna, Nightfall Alchemist",
    "Wernog, Rider's Chaplain"
  ],
  "Blue, Loyal Raptor / Owen Grady, Raptor Trainer": [
    "Blue, Loyal Raptor",
    "Owen Grady, Raptor Trainer"
  ],
  "Brallin, Skyshark Rider / Shabraz, the Skyshark": [
    "Brallin, Skyshark Rider",
    "Shabraz, the Skyshark"
  ],
  "Breeches, Brazen Plunderer / Brinelin, the Moon Kraken": [
    "Breeches, Brazen Plunderer",
    "Brinelin, the Moon Kraken"
  ],
  "Breeches, Brazen Plunderer / Bruse Tarl, Boorish Herder": [
    "Breeches, Brazen Plunderer",
    "Bruse Tarl, Boorish Herder"
  ],
  "Breeches, Brazen Plunderer / Dargo, the Shipwrecker": [
    "Breeches, Brazen Plunderer",
    "Dargo, the Shipwrecker"
  ],
  "Breeches, Brazen Plunderer / Eligeth, Crossroads Augur": [
    "Breeches, Brazen Plunderer",
    "Eligeth, Crossroads Augur"
  ],
  "Breeches, Brazen Plunderer / Esior, Wardwing Familiar": [
    "Breeches, Brazen Plunderer",
    "Esior, Wardwing Familiar"
  ],
  "Breeches, Brazen Plunderer / Falthis, Shadowcat Familiar": [
    "Breeches, Brazen Plunderer",
    "Falthis, Shadowcat Familiar"
  ],
  "Breeches, Brazen Plunderer / Francisco, Fowl Marauder": [
    "Breeches, Brazen Plunderer",
    "Francisco, Fowl Marauder"
  ],
  "Breeches, Brazen Plunderer / Ghost of Ramirez DePietro": [
    "Breeches, Brazen Plunderer",
    "Ghost of Ramirez DePietro"
  ],
  "Breeches, Brazen Plunderer / Gilanra, Caller of Wirewood": [
    "Breeches, Brazen Plunderer",
    "Gilanra, Caller of Wirewood"
  ],
  "Breeches, Brazen Plunderer / Glacian, Powerstone Engineer": [
    "Breeches, Brazen Plunderer",
    "Glacian, Powerstone Engineer"
  ],
  "Breeches, Brazen Plunderer / Halana, Kessig Ranger": [
    "Breeches, Brazen Plunderer",
    "Halana, Kessig Ranger"
  ],
  "Breeches, Brazen Plunderer / Ich-Tekik, Salvage Splicer": [
    "Breeches, Brazen Plunderer",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Breeches, Brazen Plunderer / Ikra Shidiqi, the Usurper": [
    "Breeches, Brazen Plunderer",
    "Ikra Shidiqi, the Usurper"
  ],
  "Breeches, Brazen Plunderer / Ishai, Ojutai Dragonspeaker": [
    "Breeches, Brazen Plunderer",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Breeches, Brazen Plunderer / Jeska, Thrice Reborn": [
    "Breeches, Brazen Plunderer",
    "Jeska, Thrice Reborn"
  ],
  "Breeches, Brazen Plunderer / Kamahl, Heart of Krosa": [
    "Breeches, Brazen Plunderer",
    "Kamahl, Heart of Krosa"
  ],
  "Breeches, Brazen Plunderer / Kediss, Emberclaw Familiar": [
    "Breeches, Brazen Plunderer",
    "Kediss, Emberclaw Familiar"
  ],
  "Breeches, Brazen Plunderer / Keleth, Sunmane Familiar": [
    "Breeches, Brazen Plunderer",
    "Keleth, Sunmane Familiar"
  ],
  "Breeches, Brazen Plunderer / Keskit, the Flesh Sculptor": [
    "Breeches, Brazen Plunderer",
    "Keskit, the Flesh Sculptor"
  ],
  "Breeches, Brazen Plunderer / Kodama of the East Tree": [
    "Breeches, Brazen Plunderer",
    "Kodama of the East Tree"
  ],
  "Breeches, Brazen Plunderer / Krark, the Thumbless": [
    "Breeches, Brazen Plunderer",
    "Krark, the Thumbless"
  ],
  "Breeches, Brazen Plunderer / Kraum, Ludevic's Opus": [
    "Breeches, Brazen Plunderer",
    "Kraum, Ludevic's Opus"
  ],
  "Breeches, Brazen Plunderer / Kydele, Chosen of Kruphix": [
    "Breeches, Brazen Plunderer",
    "Kydele, Chosen of Kruphix"
  ],
  "Breeches, Brazen Plunderer / Livio, Oathsworn Sentinel": [
    "Breeches, Brazen Plunderer",
    "Livio, Oathsworn Sentinel"
  ],
  "Breeches, Brazen Plunderer / Ludevic, Necro-Alchemist": [
    "Breeches, Brazen Plunderer",
    "Ludevic, Necro-Alchemist"
  ],
  "Breeches, Brazen Plunderer / Malcolm, Keen-Eyed Navigator": [
    "Breeches, Brazen Plunderer",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Breeches, Brazen Plunderer / Miara, Thorn of the Glade": [
    "Breeches, Brazen Plunderer",
    "Miara, Thorn of the Glade"
  ],
  "Breeches, Brazen Plunderer / Nadier, Agent of the Duskenel": [
    "Breeches, Brazen Plunderer",
    "Nadier, Agent of the Duskenel"
  ],
  "Breeches, Brazen Plunderer / Numa, Joraga Chieftain": [
    "Breeches, Brazen Plunderer",
    "Numa, Joraga Chieftain"
  ],
  "Breeches, Brazen Plunderer / Prava of the Steel Legion": [
    "Breeches, Brazen Plunderer",
    "Prava of the Steel Legion"
  ],
  "Breeches, Brazen Plunderer / Radiant, Serra Archangel": [
    "Breeches, Brazen Plunderer",
    "Radiant, Serra Archangel"
  ],
  "Breeches, Brazen Plunderer / Ravos, Soultender": [
    "Breeches, Brazen Plunderer",
    "Ravos, Soultender"
  ],
  "Breeches, Brazen Plunderer / Rebbec, Architect of Ascension": [
    "Breeches, Brazen Plunderer",
    "Rebbec, Architect of Ascension"
  ],
  "Breeches, Brazen Plunderer / Reyhan, Last of the Abzan": [
    "Breeches, Brazen Plunderer",
    "Reyhan, Last of the Abzan"
  ],
  "Breeches, Brazen Plunderer / Rograkh, Son of Rohgahh": [
    "Breeches, Brazen Plunderer",
    "Rograkh, Son of Rohgahh"
  ],
  "Breeches, Brazen Plunderer / Sakashima of a Thousand Faces": [
    "Breeches, Brazen Plunderer",
    "Sakashima of a Thousand Faces"
  ],
  "Breeches, Brazen Plunderer / Sengir, the Dark Baron": [
    "Breeches, Brazen Plunderer",
    "Sengir, the Dark Baron"
  ],
  "Breeches, Brazen Plunderer / Siani, Eye of the Storm": [
    "Breeches, Brazen Plunderer",
    "Siani, Eye of the Storm"
  ],
  "Breeches, Brazen Plunderer / Sidar Kondo of Jamuraa": [
    "Breeches, Brazen Plunderer",
    "Sidar Kondo of Jamuraa"
  ],
  "Breeches, Brazen Plunderer / Silas Renn, Seeker Adept": [
    "Breeches, Brazen Plunderer",
    "Silas Renn, Seeker Adept"
  ],
  "Breeches, Brazen Plunderer / Slurrk, All-Ingesting": [
    "Breeches, Brazen Plunderer",
    "Slurrk, All-Ingesting"
  ],
  "Breeches, Brazen Plunderer / Tana, the Bloodsower": [
    "Breeches, Brazen Plunderer",
    "Tana, the Bloodsower"
  ],
  "Breeches, Brazen Plunderer / Tevesh Szat, Doom of Fools": [
    "Breeches, Brazen Plunderer",
    "Tevesh Szat, Doom of Fools"
  ],
  "Breeches, Brazen Plunderer / The Prismatic Piper": [
    "Breeches, Brazen Plunderer",
    "The Prismatic Piper"
  ],
  "Breeches, Brazen Plunderer / Thrasios, Triton Hero": [
    "Breeches, Brazen Plunderer",
    "Thrasios, Triton Hero"
  ],
  "Breeches, Brazen Plunderer / Toggo, Goblin Weaponsmith": [
    "Breeches, Brazen Plunderer",
    "Toggo, Goblin Weaponsmith"
  ],
  "Breeches, Brazen Plunderer / Tormod, the Desecrator": [
    "Breeches, Brazen Plunderer",
    "Tormod, the Desecrator"
  ],
  "Breeches, Brazen Plunderer / Tymna the Weaver": [
    "Breeches, Brazen Plunderer",
    "Tymna the Weaver"
  ],
  "Breeches, Brazen Plunderer / Vial Smasher the Fierce": [
    "Breeches, Brazen Plunderer",
    "Vial Smasher the Fierce"
  ],
  "Breeches, Brazen Plunderer / Yoshimaru, Ever Faithful": [
    "Breeches, Brazen Plunderer",
    "Yoshimaru, Ever Faithful"
  ],
  "Brinelin, the Moon Kraken / Bruse Tarl, Boorish Herder": [
    "Brinelin, the Moon Kraken",
    "Bruse Tarl, Boorish Herder"
  ],
  "Brinelin, the Moon Kraken / Dargo, the Shipwrecker": [
    "Brinelin, the Moon Kraken",
    "Dargo, the Shipwrecker"
  ],
  "Brinelin, the Moon Kraken / Eligeth, Crossroads Augur": [
    "Brinelin, the Moon Kraken",
    "Eligeth, Crossroads Augur"
  ],
  "Brinelin, the Moon Kraken / Esior, Wardwing Familiar": [
    "Brinelin, the Moon Kraken",
    "Esior, Wardwing Familiar"
  ],
  "Brinelin, the Moon Kraken / Falthis, Shadowcat Familiar": [
    "Brinelin, the Moon Kraken",
    "Falthis, Shadowcat Familiar"
  ],
  "Brinelin, the Moon Kraken / Francisco, Fowl Marauder": [
    "Brinelin, the Moon Kraken",
    "Francisco, Fowl Marauder"
  ],
  "Brinelin, the Moon Kraken / Ghost of Ramirez DePietro": [
    "Brinelin, the Moon Kraken",
    "Ghost of Ramirez DePietro"
  ],
  "Brinelin, the Moon Kraken / Gilanra, Caller of Wirewood": [
    "Brinelin, the Moon Kraken",
    "Gilanra, Caller of Wirewood"
  ],
  "Brinelin, the Moon Kraken / Glacian, Powerstone Engineer": [
    "Brinelin, the Moon Kraken",
    "Glacian, Powerstone Engineer"
  ],
  "Brinelin, the Moon Kraken / Halana, Kessig Ranger": [
    "Brinelin, the Moon Kraken",
    "Halana, Kessig Ranger"
  ],
  "Brinelin, the Moon Kraken / Ich-Tekik, Salvage Splicer": [
    "Brinelin, the Moon Kraken",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Brinelin, the Moon Kraken / Ikra Shidiqi, the Usurper": [
    "Brinelin, the Moon Kraken",
    "Ikra Shidiqi, the Usurper"
  ],
  "Brinelin, the Moon Kraken / Ishai, Ojutai Dragonspeaker": [
    "Brinelin, the Moon Kraken",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Brinelin, the Moon Kraken / Jeska, Thrice Reborn": [
    "Brinelin, the Moon Kraken",
    "Jeska, Thrice Reborn"
  ],
  "Brinelin, the Moon Kraken / Kamahl, Heart of Krosa": [
    "Brinelin, the Moon Kraken",
    "Kamahl, Heart of Krosa"
  ],
  "Brinelin, the Moon Kraken / Kediss, Emberclaw Familiar": [
    "Brinelin, the Moon Kraken",
    "Kediss, Emberclaw Familiar"
  ],
  "Brinelin, the Moon Kraken / Keleth, Sunmane Familiar": [
    "Brinelin, the Moon Kraken",
    "Keleth, Sunmane Familiar"
  ],
  "Brinelin, the Moon Kraken / Keskit, the Flesh Sculptor": [
    "Brinelin, the Moon Kraken",
    "Keskit, the Flesh Sculptor"
  ],
  "Brinelin, the Moon Kraken / Kodama of the East Tree": [
    "Brinelin, the Moon Kraken",
    "Kodama of the East Tree"
  ],
  "Brinelin, the Moon Kraken / Krark, the Thumbless": [
    "Brinelin, the Moon Kraken",
    "Krark, the Thumbless"
  ],
  "Brinelin, the Moon Kraken / Kraum, Ludevic's Opus": [
    "Brinelin, the Moon Kraken",
    "Kraum, Ludevic's Opus"
  ],
  "Brinelin, the Moon Kraken / Kydele, Chosen of Kruphix": [
    "Brinelin, the Moon Kraken",
    "Kydele, Chosen of Kruphix"
  ],
  "Brinelin, the Moon Kraken / Livio, Oathsworn Sentinel": [
    "Brinelin, the Moon Kraken",
    "Livio, Oathsworn Sentinel"
  ],
  "Brinelin, the Moon Kraken / Ludevic, Necro-Alchemist": [
    "Brinelin, the Moon Kraken",
    "Ludevic, Necro-Alchemist"
  ],
  "Brinelin, the Moon Kraken / Malcolm, Keen-Eyed Navigator": [
    "Brinelin, the Moon Kraken",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Brinelin, the Moon Kraken / Miara, Thorn of the Glade": [
    "Brinelin, the Moon Kraken",
    "Miara, Thorn of the Glade"
  ],
  "Brinelin, the Moon Kraken / Nadier, Agent of the Duskenel": [
    "Brinelin, the Moon Kraken",
    "Nadier, Agent of the Duskenel"
  ],
  "Brinelin, the Moon Kraken / Numa, Joraga Chieftain": [
    "Brinelin, the Moon Kraken",
    "Numa, Joraga Chieftain"
  ],
  "Brinelin, the Moon Kraken / Prava of the Steel Legion": [
    "Brinelin, the Moon Kraken",
    "Prava of the Steel Legion"
  ],
  "Brinelin, the Moon Kraken / Radiant, Serra Archangel": [
    "Brinelin, the Moon Kraken",
    "Radiant, Serra Archangel"
  ],
  "Brinelin, the Moon Kraken / Ravos, Soultender": [
    "Brinelin, the Moon Kraken",
    "Ravos, Soultender"
  ],
  "Brinelin, the Moon Kraken / Rebbec, Architect of Ascension": [
    "Brinelin, the Moon Kraken",
    "Rebbec, Architect of Ascension"
  ],
  "Brinelin, the Moon Kraken / Reyhan, Last of the Abzan": [
    "Brinelin, the Moon Kraken",
    "Reyhan, Last of the Abzan"
  ],
  "Brinelin, the Moon Kraken / Rograkh, Son of Rohgahh": [
    "Brinelin, the Moon Kraken",
    "Rograkh, Son of Rohgahh"
  ],
  "Brinelin, the Moon Kraken / Sakashima of a Thousand Faces": [
    "Brinelin, the Moon Kraken",
    "Sakashima of a Thousand Faces"
  ],
  "Brinelin, the Moon Kraken / Sengir, the Dark Baron": [
    "Brinelin, the Moon Kraken",
    "Sengir, the Dark Baron"
  ],
  "Brinelin, the Moon Kraken / Siani, Eye of the Storm": [
    "Brinelin, the Moon Kraken",
    "Siani, Eye of the Storm"
  ],
  "Brinelin, the Moon Kraken / Sidar Kondo of Jamuraa": [
    "Brinelin, the Moon Kraken",
    "Sidar Kondo of Jamuraa"
  ],
  "Brinelin, the Moon Kraken / Silas Renn, Seeker Adept": [
    "Brinelin, the Moon Kraken",
    "Silas Renn, Seeker Adept"
  ],
  "Brinelin, the Moon Kraken / Slurrk, All-Ingesting": [
    "Brinelin, the Moon Kraken",
    "Slurrk, All-Ingesting"
  ],
  "Brinelin, the Moon Kraken / Tana, the Bloodsower": [
    "Brinelin, the Moon Kraken",
    "Tana, the Bloodsower"
  ],
  "Brinelin, the Moon Kraken / Tevesh Szat, Doom of Fools": [
    "Brinelin, the Moon Kraken",
    "Tevesh Szat, Doom of Fools"
  ],
  "Brinelin, the Moon Kraken / The Prismatic Piper": [
    "Brinelin, the Moon Kraken",
    "The Prismatic Piper"
  ],
  "Brinelin, the Moon Kraken / Thrasios, Triton Hero": [
    "Brinelin, the Moon Kraken",
    "Thrasios, Triton Hero"
  ],
  "Brinelin, the Moon Kraken / Toggo, Goblin Weaponsmith": [
    "Brinelin, the Moon Kraken",
    "Toggo, Goblin Weaponsmith"
  ],
  "Brinelin, the Moon Kraken / Tormod, the Desecrator": [
    "Brinelin, the Moon Kraken",
    "Tormod, the Desecrator"
  ],
  "Brinelin, the Moon Kraken / Tymna the Weaver": [
    "Brinelin, the Moon Kraken",
    "Tymna the Weaver"
  ],
  "Brinelin, the Moon Kraken / Vial Smasher the Fierce": [
    "Brinelin, the Moon Kraken",
    "Vial Smasher the Fierce"
  ],
  "Brinelin, the Moon Kraken / Yoshimaru, Ever Faithful": [
    "Brinelin, the Moon Kraken",
    "Yoshimaru, Ever Faithful"
  ],
  "Bruse Tarl, Boorish Herder / Dargo, the Shipwrecker": [
    "Bruse Tarl, Boorish Herder",
    "Dargo, the Shipwrecker"
  ],
  "Bruse Tarl, Boorish Herder / Eligeth, Crossroads Augur": [
    "Bruse Tarl, Boorish Herder",
    "Eligeth, Crossroads Augur"
  ],
  "Bruse Tarl, Boorish Herder / Esior, Wardwing Familiar": [
    "Bruse Tarl, Boorish Herder",
    "Esior, Wardwing Familiar"
  ],
  "Bruse Tarl, Boorish Herder / Falthis, Shadowcat Familiar": [
    "Bruse Tarl, Boorish Herder",
    "Falthis, Shadowcat Familiar"
  ],
  "Bruse Tarl, Boorish Herder / Francisco, Fowl Marauder": [
    "Bruse Tarl, Boorish Herder",
    "Francisco, Fowl Marauder"
  ],
  "Bruse Tarl, Boorish Herder / Ghost of Ramirez DePietro": [
    "Bruse Tarl, Boorish Herder",
    "Ghost of Ramirez DePietro"
  ],
  "Bruse Tarl, Boorish Herder / Gilanra, Caller of Wirewood": [
    "Bruse Tarl, Boorish Herder",
    "Gilanra, Caller of Wirewood"
  ],
  "Bruse Tarl, Boorish Herder / Glacian, Powerstone Engineer": [
    "Bruse Tarl, Boorish Herder",
    "Glacian, Powerstone Engineer"
  ],
  "Bruse Tarl, Boorish Herder / Halana, Kessig Ranger": [
    "Bruse Tarl, Boorish Herder",
    "Halana, Kessig Ranger"
  ],
  "Bruse Tarl, Boorish Herder / Ich-Tekik, Salvage Splicer": [
    "Bruse Tarl, Boorish Herder",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Bruse Tarl, Boorish Herder / Ikra Shidiqi, the Usurper": [
    "Bruse Tarl, Boorish Herder",
    "Ikra Shidiqi, the Usurper"
  ],
  "Bruse Tarl, Boorish Herder / Ishai, Ojutai Dragonspeaker": [
    "Bruse Tarl, Boorish Herder",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Bruse Tarl, Boorish Herder / Jeska, Thrice Reborn": [
    "Bruse Tarl, Boorish Herder",
    "Jeska, Thrice Reborn"
  ],
  "Bruse Tarl, Boorish Herder / Kamahl, Heart of Krosa": [
    "Bruse Tarl, Boorish Herder",
    "Kamahl, Heart of Krosa"
  ],
  "Bruse Tarl, Boorish Herder / Kediss, Emberclaw Familiar": [
    "Bruse Tarl, Boorish Herder",
    "Kediss, Emberclaw Familiar"
  ],
  "Bruse Tarl, Boorish Herder / Keleth, Sunmane Familiar": [
    "Bruse Tarl, Boorish Herder",
    "Keleth, Sunmane Familiar"
  ],
  "Bruse Tarl, Boorish Herder / Keskit, the Flesh Sculptor": [
    "Bruse Tarl, Boorish Herder",
    "Keskit, the Flesh Sculptor"
  ],
  "Bruse Tarl, Boorish Herder / Kodama of the East Tree": [
    "Bruse Tarl, Boorish Herder",
    "Kodama of the East Tree"
  ],
  "Bruse Tarl, Boorish Herder / Krark, the Thumbless": [
    "Bruse Tarl, Boorish Herder",
    "Krark, the Thumbless"
  ],
  "Bruse Tarl, Boorish Herder / Kraum, Ludevic's Opus": [
    "Bruse Tarl, Boorish Herder",
    "Kraum, Ludevic's Opus"
  ],
  "Bruse Tarl, Boorish Herder / Kydele, Chosen of Kruphix": [
    "Bruse Tarl, Boorish Herder",
    "Kydele, Chosen of Kruphix"
  ],
  "Bruse Tarl, Boorish Herder / Livio, Oathsworn Sentinel": [
    "Bruse Tarl, Boorish Herder",
    "Livio, Oathsworn Sentinel"
  ],
  "Bruse Tarl, Boorish Herder / Ludevic, Necro-Alchemist": [
    "Bruse Tarl, Boorish Herder",
    "Ludevic, Necro-Alchemist"
  ],
  "Bruse Tarl, Boorish Herder / Malcolm, Keen-Eyed Navigator": [
    "Bruse Tarl, Boorish Herder",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Bruse Tarl, Boorish Herder / Miara, Thorn of the Glade": [
    "Bruse Tarl, Boorish Herder",
    "Miara, Thorn of the Glade"
  ],
  "Bruse Tarl, Boorish Herder / Nadier, Agent of the Duskenel": [
    "Bruse Tarl, Boorish Herder",
    "Nadier, Agent of the Duskenel"
  ],
  "Bruse Tarl, Boorish Herder / Numa, Joraga Chieftain": [
    "Bruse Tarl, Boorish Herder",
    "Numa, Joraga Chieftain"
  ],
  "Bruse Tarl, Boorish Herder / Prava of the Steel Legion": [
    "Bruse Tarl, Boorish Herder",
    "Prava of the Steel Legion"
  ],
  "Bruse Tarl, Boorish Herder / Radiant, Serra Archangel": [
    "Bruse Tarl, Boorish Herder",
    "Radiant, Serra Archangel"
  ],
  "Bruse Tarl, Boorish Herder / Ravos, Soultender": [
    "Bruse Tarl, Boorish Herder",
    "Ravos, Soultender"
  ],
  "Bruse Tarl, Boorish Herder / Rebbec, Architect of Ascension": [
    "Bruse Tarl, Boorish Herder",
    "Rebbec, Architect of Ascension"
  ],
  "Bruse Tarl, Boorish Herder / Reyhan, Last of the Abzan": [
    "Bruse Tarl, Boorish Herder",
    "Reyhan, Last of the Abzan"
  ],
  "Bruse Tarl, Boorish Herder / Rograkh, Son of Rohgahh": [
    "Bruse Tarl, Boorish Herder",
    "Rograkh, Son of Rohgahh"
  ],
  "Bruse Tarl, Boorish Herder / Sakashima of a Thousand Faces": [
    "Bruse Tarl, Boorish Herder",
    "Sakashima of a Thousand Faces"
  ],
  "Bruse Tarl, Boorish Herder / Sengir, the Dark Baron": [
    "Bruse Tarl, Boorish Herder",
    "Sengir, the Dark Baron"
  ],
  "Bruse Tarl, Boorish Herder / Siani, Eye of the Storm": [
    "Bruse Tarl, Boorish Herder",
    "Siani, Eye of the Storm"
  ],
  "Bruse Tarl, Boorish Herder / Sidar Kondo of Jamuraa": [
    "Bruse Tarl, Boorish Herder",
    "Sidar Kondo of Jamuraa"
  ],
  "Bruse Tarl, Boorish Herder / Silas Renn, Seeker Adept": [
    "Bruse Tarl, Boorish Herder",
    "Silas Renn, Seeker Adept"
  ],
  "Bruse Tarl, Boorish Herder / Slurrk, All-Ingesting": [
    "Bruse Tarl, Boorish Herder",
    "Slurrk, All-Ingesting"
  ],
  "Bruse Tarl, Boorish Herder / Tana, the Bloodsower": [
    "Bruse Tarl, Boorish Herder",
    "Tana, the Bloodsower"
  ],
  "Bruse Tarl, Boorish Herder / Tevesh Szat, Doom of Fools": [
    "Bruse Tarl, Boorish Herder",
    "Tevesh Szat, Doom of Fools"
  ],
  "Bruse Tarl, Boorish Herder / The Prismatic Piper": [
    "Bruse Tarl, Boorish Herder",
    "The Prismatic Piper"
  ],
  "Bruse Tarl, Boorish Herder / Thrasios, Triton Hero": [
    "Bruse Tarl, Boorish Herder",
    "Thrasios, Triton Hero"
  ],
  "Bruse Tarl, Boorish Herder / Toggo, Goblin Weaponsmith": [
    "Bruse Tarl, Boorish Herder",
    "Toggo, Goblin Weaponsmith"
  ],
  "Bruse Tarl, Boorish Herder / Tormod, the Desecrator": [
    "Bruse Tarl, Boorish Herder",
    "Tormod, the Desecrator"
  ],
  "Bruse Tarl, Boorish Herder / Tymna the Weaver": [
    "Bruse Tarl, Boorish Herder",
    "Tymna the Weaver"
  ],
  "Bruse Tarl, Boorish Herder / Vial Smasher the Fierce": [
    "Bruse Tarl, Boorish Herder",
    "Vial Smasher the Fierce"
  ],
  "Bruse Tarl, Boorish Herder / Yoshimaru, Ever Faithful": [
    "Bruse Tarl, Boorish Herder",
    "Yoshimaru, Ever Faithful"
  ],
  "Burakos, Party Leader / Candlekeep Sage": [
    "Burakos, Party Leader",
    "Candlekeep Sage"
  ],
  "Burakos, Party Leader / Clan Crafter": [
    "Burakos, Party Leader",
    "Clan Crafter"
  ],
  "Burakos, Party Leader / Cloakwood Hermit": [
    "Burakos, Party Leader",
    "Cloakwood Hermit"
  ],
  "Burakos, Party Leader / Criminal Past": [
    "Burakos, Party Leader",
    "Criminal Past"
  ],
  "Burakos, Party Leader / Cultist of the Absolute": [
    "Burakos, Party Leader",
    "Cultist of the Absolute"
  ],
  "Burakos, Party Leader / Dragon Cultist": [
    "Burakos, Party Leader",
    "Dragon Cultist"
  ],
  "Burakos, Party Leader / Dungeon Delver": [
    "Burakos, Party Leader",
    "Dungeon Delver"
  ],
  "Burakos, Party Leader / Faceless One": [
    "Burakos, Party Leader",
    "Faceless One"
  ],
  "Burakos, Party Leader / Far Traveler": [
    "Burakos, Party Leader",
    "Far Traveler"
  ],
  "Burakos, Party Leader / Feywild Visitor": [
    "Burakos, Party Leader",
    "Feywild Visitor"
  ],
  "Burakos, Party Leader / Flaming Fist": [
    "Burakos, Party Leader",
    "Flaming Fist"
  ],
  "Burakos, Party Leader / Folk Hero": [
    "Burakos, Party Leader",
    "Folk Hero"
  ],
  "Burakos, Party Leader / Guild Artisan": [
    "Burakos, Party Leader",
    "Guild Artisan"
  ],
  "Burakos, Party Leader / Hardy Outlander": [
    "Burakos, Party Leader",
    "Hardy Outlander"
  ],
  "Burakos, Party Leader / Haunted One": [
    "Burakos, Party Leader",
    "Haunted One"
  ],
  "Burakos, Party Leader / Inspiring Leader": [
    "Burakos, Party Leader",
    "Inspiring Leader"
  ],
  "Burakos, Party Leader / Master Chef": [
    "Burakos, Party Leader",
    "Master Chef"
  ],
  "Burakos, Party Leader / Noble Heritage": [
    "Burakos, Party Leader",
    "Noble Heritage"
  ],
  "Burakos, Party Leader / Passionate Archaeologist": [
    "Burakos, Party Leader",
    "Passionate Archaeologist"
  ],
  "Burakos, Party Leader / Popular Entertainer": [
    "Burakos, Party Leader",
    "Popular Entertainer"
  ],
  "Burakos, Party Leader / Raised by Giants": [
    "Burakos, Party Leader",
    "Raised by Giants"
  ],
  "Burakos, Party Leader / Scion of Halaster": [
    "Burakos, Party Leader",
    "Scion of Halaster"
  ],
  "Burakos, Party Leader / Shameless Charlatan": [
    "Burakos, Party Leader",
    "Shameless Charlatan"
  ],
  "Burakos, Party Leader / Street Urchin": [
    "Burakos, Party Leader",
    "Street Urchin"
  ],
  "Burakos, Party Leader / Sword Coast Sailor": [
    "Burakos, Party Leader",
    "Sword Coast Sailor"
  ],
  "Burakos, Party Leader / Tavern Brawler": [
    "Burakos, Party Leader",
    "Tavern Brawler"
  ],
  "Burakos, Party Leader / Veteran Soldier": [
    "Burakos, Party Leader",
    "Veteran Soldier"
  ],
  "Candlekeep Sage / Durnan of the Yawning Portal": [
    "Candlekeep Sage",
    "Durnan of the Yawning Portal"
  ],
  "Candlekeep Sage / Ellyn Harbreeze, Busybody": [
    "Candlekeep Sage",
    "Ellyn Harbreeze, Busybody"
  ],
  "Candlekeep Sage / Erinis, Gloom Stalker": [
    "Candlekeep Sage",
    "Erinis, Gloom Stalker"
  ],
  "Candlekeep Sage / Faceless One": [
    "Candlekeep Sage",
    "Faceless One"
  ],
  "Candlekeep Sage / Gale, Waterdeep Prodigy": [
    "Candlekeep Sage",
    "Gale, Waterdeep Prodigy"
  ],
  "Candlekeep Sage / Ganax, Astral Hunter": [
    "Candlekeep Sage",
    "Ganax, Astral Hunter"
  ],
  "Candlekeep Sage / Gut, True Soul Zealot": [
    "Candlekeep Sage",
    "Gut, True Soul Zealot"
  ],
  "Candlekeep Sage / Halsin, Emerald Archdruid": [
    "Candlekeep Sage",
    "Halsin, Emerald Archdruid"
  ],
  "Candlekeep Sage / Imoen, Mystic Trickster": [
    "Candlekeep Sage",
    "Imoen, Mystic Trickster"
  ],
  "Candlekeep Sage / Jaheira, Friend of the Forest": [
    "Candlekeep Sage",
    "Jaheira, Friend of the Forest"
  ],
  "Candlekeep Sage / Karlach, Fury of Avernus": [
    "Candlekeep Sage",
    "Karlach, Fury of Avernus"
  ],
  "Candlekeep Sage / Lae'zel, Vlaakith's Champion": [
    "Candlekeep Sage",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Candlekeep Sage / Livaan, Cultist of Tiamat": [
    "Candlekeep Sage",
    "Livaan, Cultist of Tiamat"
  ],
  "Candlekeep Sage / Lulu, Loyal Hollyphant": [
    "Candlekeep Sage",
    "Lulu, Loyal Hollyphant"
  ],
  "Candlekeep Sage / Rasaad yn Bashir": [
    "Candlekeep Sage",
    "Rasaad yn Bashir"
  ],
  "Candlekeep Sage / Renari, Merchant of Marvels": [
    "Candlekeep Sage",
    "Renari, Merchant of Marvels"
  ],
  "Candlekeep Sage / Safana, Calimport Cutthroat": [
    "Candlekeep Sage",
    "Safana, Calimport Cutthroat"
  ],
  "Candlekeep Sage / Sarevok, Deathbringer": [
    "Candlekeep Sage",
    "Sarevok, Deathbringer"
  ],
  "Candlekeep Sage / Shadowheart, Dark Justiciar": [
    "Candlekeep Sage",
    "Shadowheart, Dark Justiciar"
  ],
  "Candlekeep Sage / Sivriss, Nightmare Speaker": [
    "Candlekeep Sage",
    "Sivriss, Nightmare Speaker"
  ],
  "Candlekeep Sage / Skanos Dragonheart": [
    "Candlekeep Sage",
    "Skanos Dragonheart"
  ],
  "Candlekeep Sage / Vhal, Candlekeep Researcher": [
    "Candlekeep Sage",
    "Vhal, Candlekeep Researcher"
  ],
  "Candlekeep Sage / Viconia, Drow Apostate": [
    "Candlekeep Sage",
    "Viconia, Drow Apostate"
  ],
  "Candlekeep Sage / Volo, Itinerant Scholar": [
    "Candlekeep Sage",
    "Volo, Itinerant Scholar"
  ],
  "Candlekeep Sage / Wilson, Refined Grizzly": [
    "Candlekeep Sage",
    "Wilson, Refined Grizzly"
  ],
  "Candlekeep Sage / Wyll, Blade of Frontiers": [
    "Candlekeep Sage",
    "Wyll, Blade of Frontiers"
  ],
  "Candlekeep Sage / Zellix, Sanity Flayer": [
    "Candlekeep Sage",
    "Zellix, Sanity Flayer"
  ],
  "Cazur, Ruthless Stalker / Ukkima, Stalking Shadow": [
    "Ukkima, Stalking Shadow",
    "Cazur, Ruthless Stalker"
  ],
  "Cecily, Haunted Mage / Elmar, Ulvenwald Informant": [
    "Cecily, Haunted Mage",
    "Elmar, Ulvenwald Informant"
  ],
  "Cecily, Haunted Mage / Hargilde, Kindly Runechanter": [
    "Cecily, Haunted Mage",
    "Hargilde, Kindly Runechanter"
  ],
  "Cecily, Haunted Mage / Othelm, Sigardian Outcast": [
    "Cecily, Haunted Mage",
    "Othelm, Sigardian Outcast"
  ],
  "Cecily, Haunted Mage / Sophina, Spearsage Deserter": [
    "Cecily, Haunted Mage",
    "Sophina, Spearsage Deserter"
  ],
  "Cecily, Haunted Mage / Wernog, Rider's Chaplain": [
    "Cecily, Haunted Mage",
    "Wernog, Rider's Chaplain"
  ],
  "Clan Crafter / Durnan of the Yawning Portal": [
    "Clan Crafter",
    "Durnan of the Yawning Portal"
  ],
  "Clan Crafter / Ellyn Harbreeze, Busybody": [
    "Clan Crafter",
    "Ellyn Harbreeze, Busybody"
  ],
  "Clan Crafter / Erinis, Gloom Stalker": [
    "Clan Crafter",
    "Erinis, Gloom Stalker"
  ],
  "Clan Crafter / Faceless One": [
    "Clan Crafter",
    "Faceless One"
  ],
  "Clan Crafter / Gale, Waterdeep Prodigy": [
    "Clan Crafter",
    "Gale, Waterdeep Prodigy"
  ],
  "Clan Crafter / Ganax, Astral Hunter": [
    "Clan Crafter",
    "Ganax, Astral Hunter"
  ],
  "Clan Crafter / Gut, True Soul Zealot": [
    "Clan Crafter",
    "Gut, True Soul Zealot"
  ],
  "Clan Crafter / Halsin, Emerald Archdruid": [
    "Clan Crafter",
    "Halsin, Emerald Archdruid"
  ],
  "Clan Crafter / Imoen, Mystic Trickster": [
    "Clan Crafter",
    "Imoen, Mystic Trickster"
  ],
  "Clan Crafter / Jaheira, Friend of the Forest": [
    "Clan Crafter",
    "Jaheira, Friend of the Forest"
  ],
  "Clan Crafter / Karlach, Fury of Avernus": [
    "Clan Crafter",
    "Karlach, Fury of Avernus"
  ],
  "Clan Crafter / Lae'zel, Vlaakith's Champion": [
    "Clan Crafter",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Clan Crafter / Livaan, Cultist of Tiamat": [
    "Clan Crafter",
    "Livaan, Cultist of Tiamat"
  ],
  "Clan Crafter / Lulu, Loyal Hollyphant": [
    "Clan Crafter",
    "Lulu, Loyal Hollyphant"
  ],
  "Clan Crafter / Rasaad yn Bashir": [
    "Clan Crafter",
    "Rasaad yn Bashir"
  ],
  "Clan Crafter / Renari, Merchant of Marvels": [
    "Clan Crafter",
    "Renari, Merchant of Marvels"
  ],
  "Clan Crafter / Safana, Calimport Cutthroat": [
    "Clan Crafter",
    "Safana, Calimport Cutthroat"
  ],
  "Clan Crafter / Sarevok, Deathbringer": [
    "Clan Crafter",
    "Sarevok, Deathbringer"
  ],
  "Clan Crafter / Shadowheart, Dark Justiciar": [
    "Clan Crafter",
    "Shadowheart, Dark Justiciar"
  ],
  "Clan Crafter / Sivriss, Nightmare Speaker": [
    "Clan Crafter",
    "Sivriss, Nightmare Speaker"
  ],
  "Clan Crafter / Skanos Dragonheart": [
    "Clan Crafter",
    "Skanos Dragonheart"
  ],
  "Clan Crafter / Vhal, Candlekeep Researcher": [
    "Clan Crafter",
    "Vhal, Candlekeep Researcher"
  ],
  "Clan Crafter / Viconia, Drow Apostate": [
    "Clan Crafter",
    "Viconia, Drow Apostate"
  ],
  "Clan Crafter / Volo, Itinerant Scholar": [
    "Clan Crafter",
    "Volo, Itinerant Scholar"
  ],
  "Clan Crafter / Wilson, Refined Grizzly": [
    "Clan Crafter",
    "Wilson, Refined Grizzly"
  ],
  "Clan Crafter / Wyll, Blade of Frontiers": [
    "Clan Crafter",
    "Wyll, Blade of Frontiers"
  ],
  "Clan Crafter / Zellix, Sanity Flayer": [
    "Clan Crafter",
    "Zellix, Sanity Flayer"
  ],
  "Clara Oswald / The Eighth Doctor": [
    "Clara Oswald",
    "The Eighth Doctor"
  ],
  "Clara Oswald / The Eleventh Doctor": [
    "Clara Oswald",
    "The Eleventh Doctor"
  ],
  "Clara Oswald / The Fifteenth Doctor": [
    "Clara Oswald",
    "The Fifteenth Doctor"
  ],
  "Clara Oswald / The Fifth Doctor": [
    "Clara Oswald",
    "The Fifth Doctor"
  ],
  "Clara Oswald / The First Doctor": [
    "Clara Oswald",
    "The First Doctor"
  ],
  "Clara Oswald / The Fourteenth Doctor": [
    "Clara Oswald",
    "The Fourteenth Doctor"
  ],
  "Clara Oswald / The Fourth Doctor": [
    "Clara Oswald",
    "The Fourth Doctor"
  ],
  "Clara Oswald / The Fugitive Doctor": [
    "Clara Oswald",
    "The Fugitive Doctor"
  ],
  "Clara Oswald / The Ninth Doctor": [
    "Clara Oswald",
    "The Ninth Doctor"
  ],
  "Clara Oswald / The Second Doctor": [
    "Clara Oswald",
    "The Second Doctor"
  ],
  "Clara Oswald / The Seventh Doctor": [
    "Clara Oswald",
    "The Seventh Doctor"
  ],
  "Clara Oswald / The Sixth Doctor": [
    "Clara Oswald",
    "The Sixth Doctor"
  ],
  "Clara Oswald / The Tenth Doctor": [
    "Clara Oswald",
    "The Tenth Doctor"
  ],
  "Clara Oswald / The Third Doctor": [
    "Clara Oswald",
    "The Third Doctor"
  ],
  "Clara Oswald / The Thirteenth Doctor": [
    "Clara Oswald",
    "The Thirteenth Doctor"
  ],
  "Clara Oswald / The Twelfth Doctor": [
    "Clara Oswald",
    "The Twelfth Doctor"
  ],
  "Clara Oswald / The War Doctor": [
    "Clara Oswald",
    "The War Doctor"
  ],
  "Cloakwood Hermit / Durnan of the Yawning Portal": [
    "Cloakwood Hermit",
    "Durnan of the Yawning Portal"
  ],
  "Cloakwood Hermit / Ellyn Harbreeze, Busybody": [
    "Cloakwood Hermit",
    "Ellyn Harbreeze, Busybody"
  ],
  "Cloakwood Hermit / Erinis, Gloom Stalker": [
    "Cloakwood Hermit",
    "Erinis, Gloom Stalker"
  ],
  "Cloakwood Hermit / Faceless One": [
    "Cloakwood Hermit",
    "Faceless One"
  ],
  "Cloakwood Hermit / Gale, Waterdeep Prodigy": [
    "Cloakwood Hermit",
    "Gale, Waterdeep Prodigy"
  ],
  "Cloakwood Hermit / Ganax, Astral Hunter": [
    "Cloakwood Hermit",
    "Ganax, Astral Hunter"
  ],
  "Cloakwood Hermit / Gut, True Soul Zealot": [
    "Cloakwood Hermit",
    "Gut, True Soul Zealot"
  ],
  "Cloakwood Hermit / Halsin, Emerald Archdruid": [
    "Cloakwood Hermit",
    "Halsin, Emerald Archdruid"
  ],
  "Cloakwood Hermit / Imoen, Mystic Trickster": [
    "Cloakwood Hermit",
    "Imoen, Mystic Trickster"
  ],
  "Cloakwood Hermit / Jaheira, Friend of the Forest": [
    "Cloakwood Hermit",
    "Jaheira, Friend of the Forest"
  ],
  "Cloakwood Hermit / Karlach, Fury of Avernus": [
    "Cloakwood Hermit",
    "Karlach, Fury of Avernus"
  ],
  "Cloakwood Hermit / Lae'zel, Vlaakith's Champion": [
    "Cloakwood Hermit",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Cloakwood Hermit / Livaan, Cultist of Tiamat": [
    "Cloakwood Hermit",
    "Livaan, Cultist of Tiamat"
  ],
  "Cloakwood Hermit / Lulu, Loyal Hollyphant": [
    "Cloakwood Hermit",
    "Lulu, Loyal Hollyphant"
  ],
  "Cloakwood Hermit / Rasaad yn Bashir": [
    "Cloakwood Hermit",
    "Rasaad yn Bashir"
  ],
  "Cloakwood Hermit / Renari, Merchant of Marvels": [
    "Cloakwood Hermit",
    "Renari, Merchant of Marvels"
  ],
  "Cloakwood Hermit / Safana, Calimport Cutthroat": [
    "Cloakwood Hermit",
    "Safana, Calimport Cutthroat"
  ],
  "Cloakwood Hermit / Sarevok, Deathbringer": [
    "Cloakwood Hermit",
    "Sarevok, Deathbringer"
  ],
  "Cloakwood Hermit / Shadowheart, Dark Justiciar": [
    "Cloakwood Hermit",
    "Shadowheart, Dark Justiciar"
  ],
  "Cloakwood Hermit / Sivriss, Nightmare Speaker": [
    "Cloakwood Hermit",
    "Sivriss, Nightmare Speaker"
  ],
  "Cloakwood Hermit / Skanos Dragonheart": [
    "Cloakwood Hermit",
    "Skanos Dragonheart"
  ],
  "Cloakwood Hermit / Vhal, Candlekeep Researcher": [
    "Cloakwood Hermit",
    "Vhal, Candlekeep Researcher"
  ],
  "Cloakwood Hermit / Viconia, Drow Apostate": [
    "Cloakwood Hermit",
    "Viconia, Drow Apostate"
  ],
  "Cloakwood Hermit / Volo, Itinerant Scholar": [
    "Cloakwood Hermit",
    "Volo, Itinerant Scholar"
  ],
  "Cloakwood Hermit / Wilson, Refined Grizzly": [
    "Cloakwood Hermit",
    "Wilson, Refined Grizzly"
  ],
  "Cloakwood Hermit / Wyll, Blade of Frontiers": [
    "Cloakwood Hermit",
    "Wyll, Blade of Frontiers"
  ],
  "Cloakwood Hermit / Zellix, Sanity Flayer": [
    "Cloakwood Hermit",
    "Zellix, Sanity Flayer"
  ],
  "Criminal Past / Durnan of the Yawning Portal": [
    "Criminal Past",
    "Durnan of the Yawning Portal"
  ],
  "Criminal Past / Ellyn Harbreeze, Busybody": [
    "Criminal Past",
    "Ellyn Harbreeze, Busybody"
  ],
  "Criminal Past / Erinis, Gloom Stalker": [
    "Criminal Past",
    "Erinis, Gloom Stalker"
  ],
  "Criminal Past / Faceless One": [
    "Criminal Past",
    "Faceless One"
  ],
  "Criminal Past / Gale, Waterdeep Prodigy": [
    "Criminal Past",
    "Gale, Waterdeep Prodigy"
  ],
  "Criminal Past / Ganax, Astral Hunter": [
    "Criminal Past",
    "Ganax, Astral Hunter"
  ],
  "Criminal Past / Gut, True Soul Zealot": [
    "Criminal Past",
    "Gut, True Soul Zealot"
  ],
  "Criminal Past / Halsin, Emerald Archdruid": [
    "Criminal Past",
    "Halsin, Emerald Archdruid"
  ],
  "Criminal Past / Imoen, Mystic Trickster": [
    "Criminal Past",
    "Imoen, Mystic Trickster"
  ],
  "Criminal Past / Jaheira, Friend of the Forest": [
    "Criminal Past",
    "Jaheira, Friend of the Forest"
  ],
  "Criminal Past / Karlach, Fury of Avernus": [
    "Criminal Past",
    "Karlach, Fury of Avernus"
  ],
  "Criminal Past / Lae'zel, Vlaakith's Champion": [
    "Criminal Past",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Criminal Past / Livaan, Cultist of Tiamat": [
    "Criminal Past",
    "Livaan, Cultist of Tiamat"
  ],
  "Criminal Past / Lulu, Loyal Hollyphant": [
    "Criminal Past",
    "Lulu, Loyal Hollyphant"
  ],
  "Criminal Past / Rasaad yn Bashir": [
    "Criminal Past",
    "Rasaad yn Bashir"
  ],
  "Criminal Past / Renari, Merchant of Marvels": [
    "Criminal Past",
    "Renari, Merchant of Marvels"
  ],
  "Criminal Past / Safana, Calimport Cutthroat": [
    "Criminal Past",
    "Safana, Calimport Cutthroat"
  ],
  "Criminal Past / Sarevok, Deathbringer": [
    "Criminal Past",
    "Sarevok, Deathbringer"
  ],
  "Criminal Past / Shadowheart, Dark Justiciar": [
    "Criminal Past",
    "Shadowheart, Dark Justiciar"
  ],
  "Criminal Past / Sivriss, Nightmare Speaker": [
    "Criminal Past",
    "Sivriss, Nightmare Speaker"
  ],
  "Criminal Past / Skanos Dragonheart": [
    "Criminal Past",
    "Skanos Dragonheart"
  ],
  "Criminal Past / Vhal, Candlekeep Researcher": [
    "Criminal Past",
    "Vhal, Candlekeep Researcher"
  ],
  "Criminal Past / Viconia, Drow Apostate": [
    "Criminal Past",
    "Viconia, Drow Apostate"
  ],
  "Criminal Past / Volo, Itinerant Scholar": [
    "Criminal Past",
    "Volo, Itinerant Scholar"
  ],
  "Criminal Past / Wilson, Refined Grizzly": [
    "Criminal Past",
    "Wilson, Refined Grizzly"
  ],
  "Criminal Past / Wyll, Blade of Frontiers": [
    "Criminal Past",
    "Wyll, Blade of Frontiers"
  ],
  "Criminal Past / Zellix, Sanity Flayer": [
    "Criminal Past",
    "Zellix, Sanity Flayer"
  ],
  "Cultist of the Absolute / Durnan of the Yawning Portal": [
    "Cultist of the Absolute",
    "Durnan of the Yawning Portal"
  ],
  "Cultist of the Absolute / Ellyn Harbreeze, Busybody": [
    "Cultist of the Absolute",
    "Ellyn Harbreeze, Busybody"
  ],
  "Cultist of the Absolute / Erinis, Gloom Stalker": [
    "Cultist of the Absolute",
    "Erinis, Gloom Stalker"
  ],
  "Cultist of the Absolute / Faceless One": [
    "Cultist of the Absolute",
    "Faceless One"
  ],
  "Cultist of the Absolute / Gale, Waterdeep Prodigy": [
    "Cultist of the Absolute",
    "Gale, Waterdeep Prodigy"
  ],
  "Cultist of the Absolute / Ganax, Astral Hunter": [
    "Cultist of the Absolute",
    "Ganax, Astral Hunter"
  ],
  "Cultist of the Absolute / Gut, True Soul Zealot": [
    "Cultist of the Absolute",
    "Gut, True Soul Zealot"
  ],
  "Cultist of the Absolute / Halsin, Emerald Archdruid": [
    "Cultist of the Absolute",
    "Halsin, Emerald Archdruid"
  ],
  "Cultist of the Absolute / Imoen, Mystic Trickster": [
    "Cultist of the Absolute",
    "Imoen, Mystic Trickster"
  ],
  "Cultist of the Absolute / Jaheira, Friend of the Forest": [
    "Cultist of the Absolute",
    "Jaheira, Friend of the Forest"
  ],
  "Cultist of the Absolute / Karlach, Fury of Avernus": [
    "Cultist of the Absolute",
    "Karlach, Fury of Avernus"
  ],
  "Cultist of the Absolute / Lae'zel, Vlaakith's Champion": [
    "Cultist of the Absolute",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Cultist of the Absolute / Livaan, Cultist of Tiamat": [
    "Cultist of the Absolute",
    "Livaan, Cultist of Tiamat"
  ],
  "Cultist of the Absolute / Lulu, Loyal Hollyphant": [
    "Cultist of the Absolute",
    "Lulu, Loyal Hollyphant"
  ],
  "Cultist of the Absolute / Rasaad yn Bashir": [
    "Cultist of the Absolute",
    "Rasaad yn Bashir"
  ],
  "Cultist of the Absolute / Renari, Merchant of Marvels": [
    "Cultist of the Absolute",
    "Renari, Merchant of Marvels"
  ],
  "Cultist of the Absolute / Safana, Calimport Cutthroat": [
    "Cultist of the Absolute",
    "Safana, Calimport Cutthroat"
  ],
  "Cultist of the Absolute / Sarevok, Deathbringer": [
    "Cultist of the Absolute",
    "Sarevok, Deathbringer"
  ],
  "Cultist of the Absolute / Shadowheart, Dark Justiciar": [
    "Cultist of the Absolute",
    "Shadowheart, Dark Justiciar"
  ],
  "Cultist of the Absolute / Sivriss, Nightmare Speaker": [
    "Cultist of the Absolute",
    "Sivriss, Nightmare Speaker"
  ],
  "Cultist of the Absolute / Skanos Dragonheart": [
    "Cultist of the Absolute",
    "Skanos Dragonheart"
  ],
  "Cultist of the Absolute / Vhal, Candlekeep Researcher": [
    "Cultist of the Absolute",
    "Vhal, Candlekeep Researcher"
  ],
  "Cultist of the Absolute / Viconia, Drow Apostate": [
    "Cultist of the Absolute",
    "Viconia, Drow Apostate"
  ],
  "Cultist of the Absolute / Volo, Itinerant Scholar": [
    "Cultist of the Absolute",
    "Volo, Itinerant Scholar"
  ],
  "Cultist of the Absolute / Wilson, Refined Grizzly": [
    "Cultist of the Absolute",
    "Wilson, Refined Grizzly"
  ],
  "Cultist of the Absolute / Wyll, Blade of Frontiers": [
    "Cultist of the Absolute",
    "Wyll, Blade of Frontiers"
  ],
  "Cultist of the Absolute / Zellix, Sanity Flayer": [
    "Cultist of the Absolute",
    "Zellix, Sanity Flayer"
  ],
  "Dan Lewis / The Eighth Doctor": [
    "Dan Lewis",
    "The Eighth Doctor"
  ],
  "Dan Lewis / The Eleventh Doctor": [
    "Dan Lewis",
    "The Eleventh Doctor"
  ],
  "Dan Lewis / The Fifteenth Doctor": [
    "Dan Lewis",
    "The Fifteenth Doctor"
  ],
  "Dan Lewis / The Fifth Doctor": [
    "Dan Lewis",
    "The Fifth Doctor"
  ],
  "Dan Lewis / The First Doctor": [
    "Dan Lewis",
    "The First Doctor"
  ],
  "Dan Lewis / The Fourteenth Doctor": [
    "Dan Lewis",
    "The Fourteenth Doctor"
  ],
  "Dan Lewis / The Fourth Doctor": [
    "Dan Lewis",
    "The Fourth Doctor"
  ],
  "Dan Lewis / The Fugitive Doctor": [
    "Dan Lewis",
    "The Fugitive Doctor"
  ],
  "Dan Lewis / The Ninth Doctor": [
    "Dan Lewis",
    "The Ninth Doctor"
  ],
  "Dan Lewis / The Second Doctor": [
    "Dan Lewis",
    "The Second Doctor"
  ],
  "Dan Lewis / The Seventh Doctor": [
    "Dan Lewis",
    "The Seventh Doctor"
  ],
  "Dan Lewis / The Sixth Doctor": [
    "Dan Lewis",
    "The Sixth Doctor"
  ],
  "Dan Lewis / The Tenth Doctor": [
    "Dan Lewis",
    "The Tenth Doctor"
  ],
  "Dan Lewis / The Third Doctor": [
    "Dan Lewis",
    "The Third Doctor"
  ],
  "Dan Lewis / The Thirteenth Doctor": [
    "Dan Lewis",
    "The Thirteenth Doctor"
  ],
  "Dan Lewis / The Twelfth Doctor": [
    "Dan Lewis",
    "The Twelfth Doctor"
  ],
  "Dan Lewis / The War Doctor": [
    "Dan Lewis",
    "The War Doctor"
  ],
  "Dargo, the Shipwrecker / Eligeth, Crossroads Augur": [
    "Dargo, the Shipwrecker",
    "Eligeth, Crossroads Augur"
  ],
  "Dargo, the Shipwrecker / Esior, Wardwing Familiar": [
    "Dargo, the Shipwrecker",
    "Esior, Wardwing Familiar"
  ],
  "Dargo, the Shipwrecker / Falthis, Shadowcat Familiar": [
    "Dargo, the Shipwrecker",
    "Falthis, Shadowcat Familiar"
  ],
  "Dargo, the Shipwrecker / Francisco, Fowl Marauder": [
    "Dargo, the Shipwrecker",
    "Francisco, Fowl Marauder"
  ],
  "Dargo, the Shipwrecker / Ghost of Ramirez DePietro": [
    "Dargo, the Shipwrecker",
    "Ghost of Ramirez DePietro"
  ],
  "Dargo, the Shipwrecker / Gilanra, Caller of Wirewood": [
    "Dargo, the Shipwrecker",
    "Gilanra, Caller of Wirewood"
  ],
  "Dargo, the Shipwrecker / Glacian, Powerstone Engineer": [
    "Dargo, the Shipwrecker",
    "Glacian, Powerstone Engineer"
  ],
  "Dargo, the Shipwrecker / Halana, Kessig Ranger": [
    "Dargo, the Shipwrecker",
    "Halana, Kessig Ranger"
  ],
  "Dargo, the Shipwrecker / Ich-Tekik, Salvage Splicer": [
    "Dargo, the Shipwrecker",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Dargo, the Shipwrecker / Ikra Shidiqi, the Usurper": [
    "Dargo, the Shipwrecker",
    "Ikra Shidiqi, the Usurper"
  ],
  "Dargo, the Shipwrecker / Ishai, Ojutai Dragonspeaker": [
    "Dargo, the Shipwrecker",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Dargo, the Shipwrecker / Jeska, Thrice Reborn": [
    "Dargo, the Shipwrecker",
    "Jeska, Thrice Reborn"
  ],
  "Dargo, the Shipwrecker / Kamahl, Heart of Krosa": [
    "Dargo, the Shipwrecker",
    "Kamahl, Heart of Krosa"
  ],
  "Dargo, the Shipwrecker / Kediss, Emberclaw Familiar": [
    "Dargo, the Shipwrecker",
    "Kediss, Emberclaw Familiar"
  ],
  "Dargo, the Shipwrecker / Keleth, Sunmane Familiar": [
    "Dargo, the Shipwrecker",
    "Keleth, Sunmane Familiar"
  ],
  "Dargo, the Shipwrecker / Keskit, the Flesh Sculptor": [
    "Dargo, the Shipwrecker",
    "Keskit, the Flesh Sculptor"
  ],
  "Dargo, the Shipwrecker / Kodama of the East Tree": [
    "Dargo, the Shipwrecker",
    "Kodama of the East Tree"
  ],
  "Dargo, the Shipwrecker / Krark, the Thumbless": [
    "Dargo, the Shipwrecker",
    "Krark, the Thumbless"
  ],
  "Dargo, the Shipwrecker / Kraum, Ludevic's Opus": [
    "Dargo, the Shipwrecker",
    "Kraum, Ludevic's Opus"
  ],
  "Dargo, the Shipwrecker / Kydele, Chosen of Kruphix": [
    "Dargo, the Shipwrecker",
    "Kydele, Chosen of Kruphix"
  ],
  "Dargo, the Shipwrecker / Livio, Oathsworn Sentinel": [
    "Dargo, the Shipwrecker",
    "Livio, Oathsworn Sentinel"
  ],
  "Dargo, the Shipwrecker / Ludevic, Necro-Alchemist": [
    "Dargo, the Shipwrecker",
    "Ludevic, Necro-Alchemist"
  ],
  "Dargo, the Shipwrecker / Malcolm, Keen-Eyed Navigator": [
    "Dargo, the Shipwrecker",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Dargo, the Shipwrecker / Miara, Thorn of the Glade": [
    "Dargo, the Shipwrecker",
    "Miara, Thorn of the Glade"
  ],
  "Dargo, the Shipwrecker / Nadier, Agent of the Duskenel": [
    "Dargo, the Shipwrecker",
    "Nadier, Agent of the Duskenel"
  ],
  "Dargo, the Shipwrecker / Numa, Joraga Chieftain": [
    "Dargo, the Shipwrecker",
    "Numa, Joraga Chieftain"
  ],
  "Dargo, the Shipwrecker / Prava of the Steel Legion": [
    "Dargo, the Shipwrecker",
    "Prava of the Steel Legion"
  ],
  "Dargo, the Shipwrecker / Radiant, Serra Archangel": [
    "Dargo, the Shipwrecker",
    "Radiant, Serra Archangel"
  ],
  "Dargo, the Shipwrecker / Ravos, Soultender": [
    "Dargo, the Shipwrecker",
    "Ravos, Soultender"
  ],
  "Dargo, the Shipwrecker / Rebbec, Architect of Ascension": [
    "Dargo, the Shipwrecker",
    "Rebbec, Architect of Ascension"
  ],
  "Dargo, the Shipwrecker / Reyhan, Last of the Abzan": [
    "Dargo, the Shipwrecker",
    "Reyhan, Last of the Abzan"
  ],
  "Dargo, the Shipwrecker / Rograkh, Son of Rohgahh": [
    "Dargo, the Shipwrecker",
    "Rograkh, Son of Rohgahh"
  ],
  "Dargo, the Shipwrecker / Sakashima of a Thousand Faces": [
    "Dargo, the Shipwrecker",
    "Sakashima of a Thousand Faces"
  ],
  "Dargo, the Shipwrecker / Sengir, the Dark Baron": [
    "Dargo, the Shipwrecker",
    "Sengir, the Dark Baron"
  ],
  "Dargo, the Shipwrecker / Siani, Eye of the Storm": [
    "Dargo, the Shipwrecker",
    "Siani, Eye of the Storm"
  ],
  "Dargo, the Shipwrecker / Sidar Kondo of Jamuraa": [
    "Dargo, the Shipwrecker",
    "Sidar Kondo of Jamuraa"
  ],
  "Dargo, the Shipwrecker / Silas Renn, Seeker Adept": [
    "Dargo, the Shipwrecker",
    "Silas Renn, Seeker Adept"
  ],
  "Dargo, the Shipwrecker / Slurrk, All-Ingesting": [
    "Dargo, the Shipwrecker",
    "Slurrk, All-Ingesting"
  ],
  "Dargo, the Shipwrecker / Tana, the Bloodsower": [
    "Dargo, the Shipwrecker",
    "Tana, the Bloodsower"
  ],
  "Dargo, the Shipwrecker / Tevesh Szat, Doom of Fools": [
    "Dargo, the Shipwrecker",
    "Tevesh Szat, Doom of Fools"
  ],
  "Dargo, the Shipwrecker / The Prismatic Piper": [
    "Dargo, the Shipwrecker",
    "The Prismatic Piper"
  ],
  "Dargo, the Shipwrecker / Thrasios, Triton Hero": [
    "Dargo, the Shipwrecker",
    "Thrasios, Triton Hero"
  ],
  "Dargo, the Shipwrecker / Toggo, Goblin Weaponsmith": [
    "Dargo, the Shipwrecker",
    "Toggo, Goblin Weaponsmith"
  ],
  "Dargo, the Shipwrecker / Tormod, the Desecrator": [
    "Dargo, the Shipwrecker",
    "Tormod, the Desecrator"
  ],
  "Dargo, the Shipwrecker / Tymna the Weaver": [
    "Dargo, the Shipwrecker",
    "Tymna the Weaver"
  ],
  "Dargo, the Shipwrecker / Vial Smasher the Fierce": [
    "Dargo, the Shipwrecker",
    "Vial Smasher the Fierce"
  ],
  "Dargo, the Shipwrecker / Yoshimaru, Ever Faithful": [
    "Dargo, the Shipwrecker",
    "Yoshimaru, Ever Faithful"
  ],
  "Donatello, the Brains / Leonardo, the Balance": [
    "Donatello, the Brains",
    "Leonardo, the Balance"
  ],
  "Donatello, the Brains / Michelangelo, the Heart": [
    "Donatello, the Brains",
    "Michelangelo, the Heart"
  ],
  "Donatello, the Brains / Raphael, the Muscle": [
    "Donatello, the Brains",
    "Raphael, the Muscle"
  ],
  "Donatello, the Brains / Splinter, the Mentor": [
    "Donatello, the Brains",
    "Splinter, the Mentor"
  ],
  "Donna Noble / The Eighth Doctor": [
    "Donna Noble",
    "The Eighth Doctor"
  ],
  "Donna Noble / The Eleventh Doctor": [
    "Donna Noble",
    "The Eleventh Doctor"
  ],
  "Donna Noble / The Fifteenth Doctor": [
    "Donna Noble",
    "The Fifteenth Doctor"
  ],
  "Donna Noble / The Fifth Doctor": [
    "Donna Noble",
    "The Fifth Doctor"
  ],
  "Donna Noble / The First Doctor": [
    "Donna Noble",
    "The First Doctor"
  ],
  "Donna Noble / The Fourteenth Doctor": [
    "Donna Noble",
    "The Fourteenth Doctor"
  ],
  "Donna Noble / The Fourth Doctor": [
    "Donna Noble",
    "The Fourth Doctor"
  ],
  "Donna Noble / The Fugitive Doctor": [
    "Donna Noble",
    "The Fugitive Doctor"
  ],
  "Donna Noble / The Ninth Doctor": [
    "Donna Noble",
    "The Ninth Doctor"
  ],
  "Donna Noble / The Second Doctor": [
    "Donna Noble",
    "The Second Doctor"
  ],
  "Donna Noble / The Seventh Doctor": [
    "Donna Noble",
    "The Seventh Doctor"
  ],
  "Donna Noble / The Sixth Doctor": [
    "Donna Noble",
    "The Sixth Doctor"
  ],
  "Donna Noble / The Tenth Doctor": [
    "Donna Noble",
    "The Tenth Doctor"
  ],
  "Donna Noble / The Third Doctor": [
    "Donna Noble",
    "The Third Doctor"
  ],
  "Donna Noble / The Thirteenth Doctor": [
    "Donna Noble",
    "The Thirteenth Doctor"
  ],
  "Donna Noble / The Twelfth Doctor": [
    "Donna Noble",
    "The Twelfth Doctor"
  ],
  "Donna Noble / The War Doctor": [
    "Donna Noble",
    "The War Doctor"
  ],
  "Dragon Cultist / Durnan of the Yawning Portal": [
    "Dragon Cultist",
    "Durnan of the Yawning Portal"
  ],
  "Dragon Cultist / Ellyn Harbreeze, Busybody": [
    "Dragon Cultist",
    "Ellyn Harbreeze, Busybody"
  ],
  "Dragon Cultist / Erinis, Gloom Stalker": [
    "Dragon Cultist",
    "Erinis, Gloom Stalker"
  ],
  "Dragon Cultist / Faceless One": [
    "Dragon Cultist",
    "Faceless One"
  ],
  "Dragon Cultist / Gale, Waterdeep Prodigy": [
    "Dragon Cultist",
    "Gale, Waterdeep Prodigy"
  ],
  "Dragon Cultist / Ganax, Astral Hunter": [
    "Dragon Cultist",
    "Ganax, Astral Hunter"
  ],
  "Dragon Cultist / Gut, True Soul Zealot": [
    "Dragon Cultist",
    "Gut, True Soul Zealot"
  ],
  "Dragon Cultist / Halsin, Emerald Archdruid": [
    "Dragon Cultist",
    "Halsin, Emerald Archdruid"
  ],
  "Dragon Cultist / Imoen, Mystic Trickster": [
    "Dragon Cultist",
    "Imoen, Mystic Trickster"
  ],
  "Dragon Cultist / Jaheira, Friend of the Forest": [
    "Dragon Cultist",
    "Jaheira, Friend of the Forest"
  ],
  "Dragon Cultist / Karlach, Fury of Avernus": [
    "Dragon Cultist",
    "Karlach, Fury of Avernus"
  ],
  "Dragon Cultist / Lae'zel, Vlaakith's Champion": [
    "Dragon Cultist",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Dragon Cultist / Livaan, Cultist of Tiamat": [
    "Dragon Cultist",
    "Livaan, Cultist of Tiamat"
  ],
  "Dragon Cultist / Lulu, Loyal Hollyphant": [
    "Dragon Cultist",
    "Lulu, Loyal Hollyphant"
  ],
  "Dragon Cultist / Rasaad yn Bashir": [
    "Dragon Cultist",
    "Rasaad yn Bashir"
  ],
  "Dragon Cultist / Renari, Merchant of Marvels": [
    "Dragon Cultist",
    "Renari, Merchant of Marvels"
  ],
  "Dragon Cultist / Safana, Calimport Cutthroat": [
    "Dragon Cultist",
    "Safana, Calimport Cutthroat"
  ],
  "Dragon Cultist / Sarevok, Deathbringer": [
    "Dragon Cultist",
    "Sarevok, Deathbringer"
  ],
  "Dragon Cultist / Shadowheart, Dark Justiciar": [
    "Dragon Cultist",
    "Shadowheart, Dark Justiciar"
  ],
  "Dragon Cultist / Sivriss, Nightmare Speaker": [
    "Dragon Cultist",
    "Sivriss, Nightmare Speaker"
  ],
  "Dragon Cultist / Skanos Dragonheart": [
    "Dragon Cultist",
    "Skanos Dragonheart"
  ],
  "Dragon Cultist / Vhal, Candlekeep Researcher": [
    "Dragon Cultist",
    "Vhal, Candlekeep Researcher"
  ],
  "Dragon Cultist / Viconia, Drow Apostate": [
    "Dragon Cultist",
    "Viconia, Drow Apostate"
  ],
  "Dragon Cultist / Volo, Itinerant Scholar": [
    "Dragon Cultist",
    "Volo, Itinerant Scholar"
  ],
  "Dragon Cultist / Wilson, Refined Grizzly": [
    "Dragon Cultist",
    "Wilson, Refined Grizzly"
  ],
  "Dragon Cultist / Wyll, Blade of Frontiers": [
    "Dragon Cultist",
    "Wyll, Blade of Frontiers"
  ],
  "Dragon Cultist / Zellix, Sanity Flayer": [
    "Dragon Cultist",
    "Zellix, Sanity Flayer"
  ],
  "Dungeon Delver / Durnan of the Yawning Portal": [
    "Dungeon Delver",
    "Durnan of the Yawning Portal"
  ],
  "Dungeon Delver / Ellyn Harbreeze, Busybody": [
    "Dungeon Delver",
    "Ellyn Harbreeze, Busybody"
  ],
  "Dungeon Delver / Erinis, Gloom Stalker": [
    "Dungeon Delver",
    "Erinis, Gloom Stalker"
  ],
  "Dungeon Delver / Faceless One": [
    "Dungeon Delver",
    "Faceless One"
  ],
  "Dungeon Delver / Gale, Waterdeep Prodigy": [
    "Dungeon Delver",
    "Gale, Waterdeep Prodigy"
  ],
  "Dungeon Delver / Ganax, Astral Hunter": [
    "Dungeon Delver",
    "Ganax, Astral Hunter"
  ],
  "Dungeon Delver / Gut, True Soul Zealot": [
    "Dungeon Delver",
    "Gut, True Soul Zealot"
  ],
  "Dungeon Delver / Halsin, Emerald Archdruid": [
    "Dungeon Delver",
    "Halsin, Emerald Archdruid"
  ],
  "Dungeon Delver / Imoen, Mystic Trickster": [
    "Dungeon Delver",
    "Imoen, Mystic Trickster"
  ],
  "Dungeon Delver / Jaheira, Friend of the Forest": [
    "Dungeon Delver",
    "Jaheira, Friend of the Forest"
  ],
  "Dungeon Delver / Karlach, Fury of Avernus": [
    "Dungeon Delver",
    "Karlach, Fury of Avernus"
  ],
  "Dungeon Delver / Lae'zel, Vlaakith's Champion": [
    "Dungeon Delver",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Dungeon Delver / Livaan, Cultist of Tiamat": [
    "Dungeon Delver",
    "Livaan, Cultist of Tiamat"
  ],
  "Dungeon Delver / Lulu, Loyal Hollyphant": [
    "Dungeon Delver",
    "Lulu, Loyal Hollyphant"
  ],
  "Dungeon Delver / Rasaad yn Bashir": [
    "Dungeon Delver",
    "Rasaad yn Bashir"
  ],
  "Dungeon Delver / Renari, Merchant of Marvels": [
    "Dungeon Delver",
    "Renari, Merchant of Marvels"
  ],
  "Dungeon Delver / Safana, Calimport Cutthroat": [
    "Dungeon Delver",
    "Safana, Calimport Cutthroat"
  ],
  "Dungeon Delver / Sarevok, Deathbringer": [
    "Dungeon Delver",
    "Sarevok, Deathbringer"
  ],
  "Dungeon Delver / Shadowheart, Dark Justiciar": [
    "Dungeon Delver",
    "Shadowheart, Dark Justiciar"
  ],
  "Dungeon Delver / Sivriss, Nightmare Speaker": [
    "Dungeon Delver",
    "Sivriss, Nightmare Speaker"
  ],
  "Dungeon Delver / Skanos Dragonheart": [
    "Dungeon Delver",
    "Skanos Dragonheart"
  ],
  "Dungeon Delver / Vhal, Candlekeep Researcher": [
    "Dungeon Delver",
    "Vhal, Candlekeep Researcher"
  ],
  "Dungeon Delver / Viconia, Drow Apostate": [
    "Dungeon Delver",
    "Viconia, Drow Apostate"
  ],
  "Dungeon Delver / Volo, Itinerant Scholar": [
    "Dungeon Delver",
    "Volo, Itinerant Scholar"
  ],
  "Dungeon Delver / Wilson, Refined Grizzly": [
    "Dungeon Delver",
    "Wilson, Refined Grizzly"
  ],
  "Dungeon Delver / Wyll, Blade of Frontiers": [
    "Dungeon Delver",
    "Wyll, Blade of Frontiers"
  ],
  "Dungeon Delver / Zellix, Sanity Flayer": [
    "Dungeon Delver",
    "Zellix, Sanity Flayer"
  ],
  "Durnan of the Yawning Portal / Faceless One": [
    "Durnan of the Yawning Portal",
    "Faceless One"
  ],
  "Durnan of the Yawning Portal / Far Traveler": [
    "Durnan of the Yawning Portal",
    "Far Traveler"
  ],
  "Durnan of the Yawning Portal / Feywild Visitor": [
    "Durnan of the Yawning Portal",
    "Feywild Visitor"
  ],
  "Durnan of the Yawning Portal / Flaming Fist": [
    "Durnan of the Yawning Portal",
    "Flaming Fist"
  ],
  "Durnan of the Yawning Portal / Folk Hero": [
    "Durnan of the Yawning Portal",
    "Folk Hero"
  ],
  "Durnan of the Yawning Portal / Guild Artisan": [
    "Durnan of the Yawning Portal",
    "Guild Artisan"
  ],
  "Durnan of the Yawning Portal / Hardy Outlander": [
    "Durnan of the Yawning Portal",
    "Hardy Outlander"
  ],
  "Durnan of the Yawning Portal / Haunted One": [
    "Durnan of the Yawning Portal",
    "Haunted One"
  ],
  "Durnan of the Yawning Portal / Inspiring Leader": [
    "Durnan of the Yawning Portal",
    "Inspiring Leader"
  ],
  "Durnan of the Yawning Portal / Master Chef": [
    "Durnan of the Yawning Portal",
    "Master Chef"
  ],
  "Durnan of the Yawning Portal / Noble Heritage": [
    "Durnan of the Yawning Portal",
    "Noble Heritage"
  ],
  "Durnan of the Yawning Portal / Passionate Archaeologist": [
    "Durnan of the Yawning Portal",
    "Passionate Archaeologist"
  ],
  "Durnan of the Yawning Portal / Popular Entertainer": [
    "Durnan of the Yawning Portal",
    "Popular Entertainer"
  ],
  "Durnan of the Yawning Portal / Raised by Giants": [
    "Durnan of the Yawning Portal",
    "Raised by Giants"
  ],
  "Durnan of the Yawning Portal / Scion of Halaster": [
    "Durnan of the Yawning Portal",
    "Scion of Halaster"
  ],
  "Durnan of the Yawning Portal / Shameless Charlatan": [
    "Durnan of the Yawning Portal",
    "Shameless Charlatan"
  ],
  "Durnan of the Yawning Portal / Street Urchin": [
    "Durnan of the Yawning Portal",
    "Street Urchin"
  ],
  "Durnan of the Yawning Portal / Sword Coast Sailor": [
    "Durnan of the Yawning Portal",
    "Sword Coast Sailor"
  ],
  "Durnan of the Yawning Portal / Tavern Brawler": [
    "Durnan of the Yawning Portal",
    "Tavern Brawler"
  ],
  "Durnan of the Yawning Portal / Veteran Soldier": [
    "Durnan of the Yawning Portal",
    "Veteran Soldier"
  ],
  "Eligeth, Crossroads Augur / Esior, Wardwing Familiar": [
    "Eligeth, Crossroads Augur",
    "Esior, Wardwing Familiar"
  ],
  "Eligeth, Crossroads Augur / Falthis, Shadowcat Familiar": [
    "Eligeth, Crossroads Augur",
    "Falthis, Shadowcat Familiar"
  ],
  "Eligeth, Crossroads Augur / Francisco, Fowl Marauder": [
    "Eligeth, Crossroads Augur",
    "Francisco, Fowl Marauder"
  ],
  "Eligeth, Crossroads Augur / Ghost of Ramirez DePietro": [
    "Eligeth, Crossroads Augur",
    "Ghost of Ramirez DePietro"
  ],
  "Eligeth, Crossroads Augur / Gilanra, Caller of Wirewood": [
    "Eligeth, Crossroads Augur",
    "Gilanra, Caller of Wirewood"
  ],
  "Eligeth, Crossroads Augur / Glacian, Powerstone Engineer": [
    "Eligeth, Crossroads Augur",
    "Glacian, Powerstone Engineer"
  ],
  "Eligeth, Crossroads Augur / Halana, Kessig Ranger": [
    "Eligeth, Crossroads Augur",
    "Halana, Kessig Ranger"
  ],
  "Eligeth, Crossroads Augur / Ich-Tekik, Salvage Splicer": [
    "Eligeth, Crossroads Augur",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Eligeth, Crossroads Augur / Ikra Shidiqi, the Usurper": [
    "Eligeth, Crossroads Augur",
    "Ikra Shidiqi, the Usurper"
  ],
  "Eligeth, Crossroads Augur / Ishai, Ojutai Dragonspeaker": [
    "Eligeth, Crossroads Augur",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Eligeth, Crossroads Augur / Jeska, Thrice Reborn": [
    "Eligeth, Crossroads Augur",
    "Jeska, Thrice Reborn"
  ],
  "Eligeth, Crossroads Augur / Kamahl, Heart of Krosa": [
    "Eligeth, Crossroads Augur",
    "Kamahl, Heart of Krosa"
  ],
  "Eligeth, Crossroads Augur / Kediss, Emberclaw Familiar": [
    "Eligeth, Crossroads Augur",
    "Kediss, Emberclaw Familiar"
  ],
  "Eligeth, Crossroads Augur / Keleth, Sunmane Familiar": [
    "Eligeth, Crossroads Augur",
    "Keleth, Sunmane Familiar"
  ],
  "Eligeth, Crossroads Augur / Keskit, the Flesh Sculptor": [
    "Eligeth, Crossroads Augur",
    "Keskit, the Flesh Sculptor"
  ],
  "Eligeth, Crossroads Augur / Kodama of the East Tree": [
    "Eligeth, Crossroads Augur",
    "Kodama of the East Tree"
  ],
  "Eligeth, Crossroads Augur / Krark, the Thumbless": [
    "Eligeth, Crossroads Augur",
    "Krark, the Thumbless"
  ],
  "Eligeth, Crossroads Augur / Kraum, Ludevic's Opus": [
    "Eligeth, Crossroads Augur",
    "Kraum, Ludevic's Opus"
  ],
  "Eligeth, Crossroads Augur / Kydele, Chosen of Kruphix": [
    "Eligeth, Crossroads Augur",
    "Kydele, Chosen of Kruphix"
  ],
  "Eligeth, Crossroads Augur / Livio, Oathsworn Sentinel": [
    "Eligeth, Crossroads Augur",
    "Livio, Oathsworn Sentinel"
  ],
  "Eligeth, Crossroads Augur / Ludevic, Necro-Alchemist": [
    "Eligeth, Crossroads Augur",
    "Ludevic, Necro-Alchemist"
  ],
  "Eligeth, Crossroads Augur / Malcolm, Keen-Eyed Navigator": [
    "Eligeth, Crossroads Augur",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Eligeth, Crossroads Augur / Miara, Thorn of the Glade": [
    "Eligeth, Crossroads Augur",
    "Miara, Thorn of the Glade"
  ],
  "Eligeth, Crossroads Augur / Nadier, Agent of the Duskenel": [
    "Eligeth, Crossroads Augur",
    "Nadier, Agent of the Duskenel"
  ],
  "Eligeth, Crossroads Augur / Numa, Joraga Chieftain": [
    "Eligeth, Crossroads Augur",
    "Numa, Joraga Chieftain"
  ],
  "Eligeth, Crossroads Augur / Prava of the Steel Legion": [
    "Eligeth, Crossroads Augur",
    "Prava of the Steel Legion"
  ],
  "Eligeth, Crossroads Augur / Radiant, Serra Archangel": [
    "Eligeth, Crossroads Augur",
    "Radiant, Serra Archangel"
  ],
  "Eligeth, Crossroads Augur / Ravos, Soultender": [
    "Eligeth, Crossroads Augur",
    "Ravos, Soultender"
  ],
  "Eligeth, Crossroads Augur / Rebbec, Architect of Ascension": [
    "Eligeth, Crossroads Augur",
    "Rebbec, Architect of Ascension"
  ],
  "Eligeth, Crossroads Augur / Reyhan, Last of the Abzan": [
    "Eligeth, Crossroads Augur",
    "Reyhan, Last of the Abzan"
  ],
  "Eligeth, Crossroads Augur / Rograkh, Son of Rohgahh": [
    "Eligeth, Crossroads Augur",
    "Rograkh, Son of Rohgahh"
  ],
  "Eligeth, Crossroads Augur / Sakashima of a Thousand Faces": [
    "Eligeth, Crossroads Augur",
    "Sakashima of a Thousand Faces"
  ],
  "Eligeth, Crossroads Augur / Sengir, the Dark Baron": [
    "Eligeth, Crossroads Augur",
    "Sengir, the Dark Baron"
  ],
  "Eligeth, Crossroads Augur / Siani, Eye of the Storm": [
    "Eligeth, Crossroads Augur",
    "Siani, Eye of the Storm"
  ],
  "Eligeth, Crossroads Augur / Sidar Kondo of Jamuraa": [
    "Eligeth, Crossroads Augur",
    "Sidar Kondo of Jamuraa"
  ],
  "Eligeth, Crossroads Augur / Silas Renn, Seeker Adept": [
    "Eligeth, Crossroads Augur",
    "Silas Renn, Seeker Adept"
  ],
  "Eligeth, Crossroads Augur / Slurrk, All-Ingesting": [
    "Eligeth, Crossroads Augur",
    "Slurrk, All-Ingesting"
  ],
  "Eligeth, Crossroads Augur / Tana, the Bloodsower": [
    "Eligeth, Crossroads Augur",
    "Tana, the Bloodsower"
  ],
  "Eligeth, Crossroads Augur / Tevesh Szat, Doom of Fools": [
    "Eligeth, Crossroads Augur",
    "Tevesh Szat, Doom of Fools"
  ],
  "Eligeth, Crossroads Augur / The Prismatic Piper": [
    "Eligeth, Crossroads Augur",
    "The Prismatic Piper"
  ],
  "Eligeth, Crossroads Augur / Thrasios, Triton Hero": [
    "Eligeth, Crossroads Augur",
    "Thrasios, Triton Hero"
  ],
  "Eligeth, Crossroads Augur / Toggo, Goblin Weaponsmith": [
    "Eligeth, Crossroads Augur",
    "Toggo, Goblin Weaponsmith"
  ],
  "Eligeth, Crossroads Augur / Tormod, the Desecrator": [
    "Eligeth, Crossroads Augur",
    "Tormod, the Desecrator"
  ],
  "Eligeth, Crossroads Augur / Tymna the Weaver": [
    "Eligeth, Crossroads Augur",
    "Tymna the Weaver"
  ],
  "Eligeth, Crossroads Augur / Vial Smasher the Fierce": [
    "Eligeth, Crossroads Augur",
    "Vial Smasher the Fierce"
  ],
  "Eligeth, Crossroads Augur / Yoshimaru, Ever Faithful": [
    "Eligeth, Crossroads Augur",
    "Yoshimaru, Ever Faithful"
  ],
  "Ellie, Brick Master / Ellie, Vengeful Hunter": [
    "Ellie, Brick Master",
    "Ellie, Vengeful Hunter"
  ],
  "Ellie, Brick Master / Joel, Resolute Survivor": [
    "Ellie, Brick Master",
    "Joel, Resolute Survivor"
  ],
  "Ellie, Vengeful Hunter / Joel, Resolute Survivor": [
    "Ellie, Vengeful Hunter",
    "Joel, Resolute Survivor"
  ],
  "Ellyn Harbreeze, Busybody / Faceless One": [
    "Ellyn Harbreeze, Busybody",
    "Faceless One"
  ],
  "Ellyn Harbreeze, Busybody / Far Traveler": [
    "Ellyn Harbreeze, Busybody",
    "Far Traveler"
  ],
  "Ellyn Harbreeze, Busybody / Feywild Visitor": [
    "Ellyn Harbreeze, Busybody",
    "Feywild Visitor"
  ],
  "Ellyn Harbreeze, Busybody / Flaming Fist": [
    "Ellyn Harbreeze, Busybody",
    "Flaming Fist"
  ],
  "Ellyn Harbreeze, Busybody / Folk Hero": [
    "Ellyn Harbreeze, Busybody",
    "Folk Hero"
  ],
  "Ellyn Harbreeze, Busybody / Guild Artisan": [
    "Ellyn Harbreeze, Busybody",
    "Guild Artisan"
  ],
  "Ellyn Harbreeze, Busybody / Hardy Outlander": [
    "Ellyn Harbreeze, Busybody",
    "Hardy Outlander"
  ],
  "Ellyn Harbreeze, Busybody / Haunted One": [
    "Ellyn Harbreeze, Busybody",
    "Haunted One"
  ],
  "Ellyn Harbreeze, Busybody / Inspiring Leader": [
    "Ellyn Harbreeze, Busybody",
    "Inspiring Leader"
  ],
  "Ellyn Harbreeze, Busybody / Master Chef": [
    "Ellyn Harbreeze, Busybody",
    "Master Chef"
  ],
  "Ellyn Harbreeze, Busybody / Noble Heritage": [
    "Ellyn Harbreeze, Busybody",
    "Noble Heritage"
  ],
  "Ellyn Harbreeze, Busybody / Passionate Archaeologist": [
    "Ellyn Harbreeze, Busybody",
    "Passionate Archaeologist"
  ],
  "Ellyn Harbreeze, Busybody / Popular Entertainer": [
    "Ellyn Harbreeze, Busybody",
    "Popular Entertainer"
  ],
  "Ellyn Harbreeze, Busybody / Raised by Giants": [
    "Ellyn Harbreeze, Busybody",
    "Raised by Giants"
  ],
  "Ellyn Harbreeze, Busybody / Scion of Halaster": [
    "Ellyn Harbreeze, Busybody",
    "Scion of Halaster"
  ],
  "Ellyn Harbreeze, Busybody / Shameless Charlatan": [
    "Ellyn Harbreeze, Busybody",
    "Shameless Charlatan"
  ],
  "Ellyn Harbreeze, Busybody / Street Urchin": [
    "Ellyn Harbreeze, Busybody",
    "Street Urchin"
  ],
  "Ellyn Harbreeze, Busybody / Sword Coast Sailor": [
    "Ellyn Harbreeze, Busybody",
    "Sword Coast Sailor"
  ],
  "Ellyn Harbreeze, Busybody / Tavern Brawler": [
    "Ellyn Harbreeze, Busybody",
    "Tavern Brawler"
  ],
  "Ellyn Harbreeze, Busybody / Veteran Soldier": [
    "Ellyn Harbreeze, Busybody",
    "Veteran Soldier"
  ],
  "Elmar, Ulvenwald Informant / Hargilde, Kindly Runechanter": [
    "Elmar, Ulvenwald Informant",
    "Hargilde, Kindly Runechanter"
  ],
  "Elmar, Ulvenwald Informant / Othelm, Sigardian Outcast": [
    "Elmar, Ulvenwald Informant",
    "Othelm, Sigardian Outcast"
  ],
  "Elmar, Ulvenwald Informant / Sophina, Spearsage Deserter": [
    "Elmar, Ulvenwald Informant",
    "Sophina, Spearsage Deserter"
  ],
  "Elmar, Ulvenwald Informant / Wernog, Rider's Chaplain": [
    "Elmar, Ulvenwald Informant",
    "Wernog, Rider's Chaplain"
  ],
  "Erinis, Gloom Stalker / Faceless One": [
    "Erinis, Gloom Stalker",
    "Faceless One"
  ],
  "Erinis, Gloom Stalker / Far Traveler": [
    "Erinis, Gloom Stalker",
    "Far Traveler"
  ],
  "Erinis, Gloom Stalker / Feywild Visitor": [
    "Erinis, Gloom Stalker",
    "Feywild Visitor"
  ],
  "Erinis, Gloom Stalker / Flaming Fist": [
    "Erinis, Gloom Stalker",
    "Flaming Fist"
  ],
  "Erinis, Gloom Stalker / Folk Hero": [
    "Erinis, Gloom Stalker",
    "Folk Hero"
  ],
  "Erinis, Gloom Stalker / Guild Artisan": [
    "Erinis, Gloom Stalker",
    "Guild Artisan"
  ],
  "Erinis, Gloom Stalker / Hardy Outlander": [
    "Erinis, Gloom Stalker",
    "Hardy Outlander"
  ],
  "Erinis, Gloom Stalker / Haunted One": [
    "Erinis, Gloom Stalker",
    "Haunted One"
  ],
  "Erinis, Gloom Stalker / Inspiring Leader": [
    "Erinis, Gloom Stalker",
    "Inspiring Leader"
  ],
  "Erinis, Gloom Stalker / Master Chef": [
    "Erinis, Gloom Stalker",
    "Master Chef"
  ],
  "Erinis, Gloom Stalker / Noble Heritage": [
    "Erinis, Gloom Stalker",
    "Noble Heritage"
  ],
  "Erinis, Gloom Stalker / Passionate Archaeologist": [
    "Erinis, Gloom Stalker",
    "Passionate Archaeologist"
  ],
  "Erinis, Gloom Stalker / Popular Entertainer": [
    "Erinis, Gloom Stalker",
    "Popular Entertainer"
  ],
  "Erinis, Gloom Stalker / Raised by Giants": [
    "Erinis, Gloom Stalker",
    "Raised by Giants"
  ],
  "Erinis, Gloom Stalker / Scion of Halaster": [
    "Erinis, Gloom Stalker",
    "Scion of Halaster"
  ],
  "Erinis, Gloom Stalker / Shameless Charlatan": [
    "Erinis, Gloom Stalker",
    "Shameless Charlatan"
  ],
  "Erinis, Gloom Stalker / Street Urchin": [
    "Erinis, Gloom Stalker",
    "Street Urchin"
  ],
  "Erinis, Gloom Stalker / Sword Coast Sailor": [
    "Erinis, Gloom Stalker",
    "Sword Coast Sailor"
  ],
  "Erinis, Gloom Stalker / Tavern Brawler": [
    "Erinis, Gloom Stalker",
    "Tavern Brawler"
  ],
  "Erinis, Gloom Stalker / Veteran Soldier": [
    "Erinis, Gloom Stalker",
    "Veteran Soldier"
  ],
  "Esior, Wardwing Familiar / Falthis, Shadowcat Familiar": [
    "Esior, Wardwing Familiar",
    "Falthis, Shadowcat Familiar"
  ],
  "Esior, Wardwing Familiar / Francisco, Fowl Marauder": [
    "Esior, Wardwing Familiar",
    "Francisco, Fowl Marauder"
  ],
  "Esior, Wardwing Familiar / Ghost of Ramirez DePietro": [
    "Esior, Wardwing Familiar",
    "Ghost of Ramirez DePietro"
  ],
  "Esior, Wardwing Familiar / Gilanra, Caller of Wirewood": [
    "Esior, Wardwing Familiar",
    "Gilanra, Caller of Wirewood"
  ],
  "Esior, Wardwing Familiar / Glacian, Powerstone Engineer": [
    "Esior, Wardwing Familiar",
    "Glacian, Powerstone Engineer"
  ],
  "Esior, Wardwing Familiar / Halana, Kessig Ranger": [
    "Esior, Wardwing Familiar",
    "Halana, Kessig Ranger"
  ],
  "Esior, Wardwing Familiar / Ich-Tekik, Salvage Splicer": [
    "Esior, Wardwing Familiar",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Esior, Wardwing Familiar / Ikra Shidiqi, the Usurper": [
    "Esior, Wardwing Familiar",
    "Ikra Shidiqi, the Usurper"
  ],
  "Esior, Wardwing Familiar / Ishai, Ojutai Dragonspeaker": [
    "Esior, Wardwing Familiar",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Esior, Wardwing Familiar / Jeska, Thrice Reborn": [
    "Esior, Wardwing Familiar",
    "Jeska, Thrice Reborn"
  ],
  "Esior, Wardwing Familiar / Kamahl, Heart of Krosa": [
    "Esior, Wardwing Familiar",
    "Kamahl, Heart of Krosa"
  ],
  "Esior, Wardwing Familiar / Kediss, Emberclaw Familiar": [
    "Esior, Wardwing Familiar",
    "Kediss, Emberclaw Familiar"
  ],
  "Esior, Wardwing Familiar / Keleth, Sunmane Familiar": [
    "Esior, Wardwing Familiar",
    "Keleth, Sunmane Familiar"
  ],
  "Esior, Wardwing Familiar / Keskit, the Flesh Sculptor": [
    "Esior, Wardwing Familiar",
    "Keskit, the Flesh Sculptor"
  ],
  "Esior, Wardwing Familiar / Kodama of the East Tree": [
    "Esior, Wardwing Familiar",
    "Kodama of the East Tree"
  ],
  "Esior, Wardwing Familiar / Krark, the Thumbless": [
    "Esior, Wardwing Familiar",
    "Krark, the Thumbless"
  ],
  "Esior, Wardwing Familiar / Kraum, Ludevic's Opus": [
    "Esior, Wardwing Familiar",
    "Kraum, Ludevic's Opus"
  ],
  "Esior, Wardwing Familiar / Kydele, Chosen of Kruphix": [
    "Esior, Wardwing Familiar",
    "Kydele, Chosen of Kruphix"
  ],
  "Esior, Wardwing Familiar / Livio, Oathsworn Sentinel": [
    "Esior, Wardwing Familiar",
    "Livio, Oathsworn Sentinel"
  ],
  "Esior, Wardwing Familiar / Ludevic, Necro-Alchemist": [
    "Esior, Wardwing Familiar",
    "Ludevic, Necro-Alchemist"
  ],
  "Esior, Wardwing Familiar / Malcolm, Keen-Eyed Navigator": [
    "Esior, Wardwing Familiar",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Esior, Wardwing Familiar / Miara, Thorn of the Glade": [
    "Esior, Wardwing Familiar",
    "Miara, Thorn of the Glade"
  ],
  "Esior, Wardwing Familiar / Nadier, Agent of the Duskenel": [
    "Esior, Wardwing Familiar",
    "Nadier, Agent of the Duskenel"
  ],
  "Esior, Wardwing Familiar / Numa, Joraga Chieftain": [
    "Esior, Wardwing Familiar",
    "Numa, Joraga Chieftain"
  ],
  "Esior, Wardwing Familiar / Prava of the Steel Legion": [
    "Esior, Wardwing Familiar",
    "Prava of the Steel Legion"
  ],
  "Esior, Wardwing Familiar / Radiant, Serra Archangel": [
    "Esior, Wardwing Familiar",
    "Radiant, Serra Archangel"
  ],
  "Esior, Wardwing Familiar / Ravos, Soultender": [
    "Esior, Wardwing Familiar",
    "Ravos, Soultender"
  ],
  "Esior, Wardwing Familiar / Rebbec, Architect of Ascension": [
    "Esior, Wardwing Familiar",
    "Rebbec, Architect of Ascension"
  ],
  "Esior, Wardwing Familiar / Reyhan, Last of the Abzan": [
    "Esior, Wardwing Familiar",
    "Reyhan, Last of the Abzan"
  ],
  "Esior, Wardwing Familiar / Rograkh, Son of Rohgahh": [
    "Esior, Wardwing Familiar",
    "Rograkh, Son of Rohgahh"
  ],
  "Esior, Wardwing Familiar / Sakashima of a Thousand Faces": [
    "Esior, Wardwing Familiar",
    "Sakashima of a Thousand Faces"
  ],
  "Esior, Wardwing Familiar / Sengir, the Dark Baron": [
    "Esior, Wardwing Familiar",
    "Sengir, the Dark Baron"
  ],
  "Esior, Wardwing Familiar / Siani, Eye of the Storm": [
    "Esior, Wardwing Familiar",
    "Siani, Eye of the Storm"
  ],
  "Esior, Wardwing Familiar / Sidar Kondo of Jamuraa": [
    "Esior, Wardwing Familiar",
    "Sidar Kondo of Jamuraa"
  ],
  "Esior, Wardwing Familiar / Silas Renn, Seeker Adept": [
    "Esior, Wardwing Familiar",
    "Silas Renn, Seeker Adept"
  ],
  "Esior, Wardwing Familiar / Slurrk, All-Ingesting": [
    "Esior, Wardwing Familiar",
    "Slurrk, All-Ingesting"
  ],
  "Esior, Wardwing Familiar / Tana, the Bloodsower": [
    "Esior, Wardwing Familiar",
    "Tana, the Bloodsower"
  ],
  "Esior, Wardwing Familiar / Tevesh Szat, Doom of Fools": [
    "Esior, Wardwing Familiar",
    "Tevesh Szat, Doom of Fools"
  ],
  "Esior, Wardwing Familiar / The Prismatic Piper": [
    "Esior, Wardwing Familiar",
    "The Prismatic Piper"
  ],
  "Esior, Wardwing Familiar / Thrasios, Triton Hero": [
    "Esior, Wardwing Familiar",
    "Thrasios, Triton Hero"
  ],
  "Esior, Wardwing Familiar / Toggo, Goblin Weaponsmith": [
    "Esior, Wardwing Familiar",
    "Toggo, Goblin Weaponsmith"
  ],
  "Esior, Wardwing Familiar / Tormod, the Desecrator": [
    "Esior, Wardwing Familiar",
    "Tormod, the Desecrator"
  ],
  "Esior, Wardwing Familiar / Tymna the Weaver": [
    "Esior, Wardwing Familiar",
    "Tymna the Weaver"
  ],
  "Esior, Wardwing Familiar / Vial Smasher the Fierce": [
    "Esior, Wardwing Familiar",
    "Vial Smasher the Fierce"
  ],
  "Esior, Wardwing Familiar / Yoshimaru, Ever Faithful": [
    "Esior, Wardwing Familiar",
    "Yoshimaru, Ever Faithful"
  ],
  "Evie Frye / Jacob Frye": [
    "Evie Frye",
    "Jacob Frye"
  ],
  "Faceless One / Far Traveler": [
    "Faceless One",
    "Far Traveler"
  ],
  "Faceless One / Feywild Visitor": [
    "Faceless One",
    "Feywild Visitor"
  ],
  "Faceless One / Flaming Fist": [
    "Faceless One",
    "Flaming Fist"
  ],
  "Faceless One / Folk Hero": [
    "Faceless One",
    "Folk Hero"
  ],
  "Faceless One / Gale, Waterdeep Prodigy": [
    "Faceless One",
    "Gale, Waterdeep Prodigy"
  ],
  "Faceless One / Ganax, Astral Hunter": [
    "Faceless One",
    "Ganax, Astral Hunter"
  ],
  "Faceless One / Guild Artisan": [
    "Faceless One",
    "Guild Artisan"
  ],
  "Faceless One / Gut, True Soul Zealot": [
    "Faceless One",
    "Gut, True Soul Zealot"
  ],
  "Faceless One / Halsin, Emerald Archdruid": [
    "Faceless One",
    "Halsin, Emerald Archdruid"
  ],
  "Faceless One / Hardy Outlander": [
    "Faceless One",
    "Hardy Outlander"
  ],
  "Faceless One / Haunted One": [
    "Faceless One",
    "Haunted One"
  ],
  "Faceless One / Imoen, Mystic Trickster": [
    "Faceless One",
    "Imoen, Mystic Trickster"
  ],
  "Faceless One / Inspiring Leader": [
    "Faceless One",
    "Inspiring Leader"
  ],
  "Faceless One / Jaheira, Friend of the Forest": [
    "Faceless One",
    "Jaheira, Friend of the Forest"
  ],
  "Faceless One / Karlach, Fury of Avernus": [
    "Faceless One",
    "Karlach, Fury of Avernus"
  ],
  "Faceless One / Lae'zel, Vlaakith's Champion": [
    "Faceless One",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Faceless One / Livaan, Cultist of Tiamat": [
    "Faceless One",
    "Livaan, Cultist of Tiamat"
  ],
  "Faceless One / Lulu, Loyal Hollyphant": [
    "Faceless One",
    "Lulu, Loyal Hollyphant"
  ],
  "Faceless One / Master Chef": [
    "Faceless One",
    "Master Chef"
  ],
  "Faceless One / Noble Heritage": [
    "Faceless One",
    "Noble Heritage"
  ],
  "Faceless One / Passionate Archaeologist": [
    "Faceless One",
    "Passionate Archaeologist"
  ],
  "Faceless One / Popular Entertainer": [
    "Faceless One",
    "Popular Entertainer"
  ],
  "Faceless One / Raised by Giants": [
    "Faceless One",
    "Raised by Giants"
  ],
  "Faceless One / Rasaad yn Bashir": [
    "Faceless One",
    "Rasaad yn Bashir"
  ],
  "Faceless One / Renari, Merchant of Marvels": [
    "Faceless One",
    "Renari, Merchant of Marvels"
  ],
  "Faceless One / Safana, Calimport Cutthroat": [
    "Faceless One",
    "Safana, Calimport Cutthroat"
  ],
  "Faceless One / Sarevok, Deathbringer": [
    "Faceless One",
    "Sarevok, Deathbringer"
  ],
  "Faceless One / Scion of Halaster": [
    "Faceless One",
    "Scion of Halaster"
  ],
  "Faceless One / Shadowheart, Dark Justiciar": [
    "Faceless One",
    "Shadowheart, Dark Justiciar"
  ],
  "Faceless One / Shameless Charlatan": [
    "Faceless One",
    "Shameless Charlatan"
  ],
  "Faceless One / Sivriss, Nightmare Speaker": [
    "Faceless One",
    "Sivriss, Nightmare Speaker"
  ],
  "Faceless One / Skanos Dragonheart": [
    "Faceless One",
    "Skanos Dragonheart"
  ],
  "Faceless One / Street Urchin": [
    "Faceless One",
    "Street Urchin"
  ],
  "Faceless One / Sword Coast Sailor": [
    "Faceless One",
    "Sword Coast Sailor"
  ],
  "Faceless One / Tavern Brawler": [
    "Faceless One",
    "Tavern Brawler"
  ],
  "Faceless One / Veteran Soldier": [
    "Faceless One",
    "Veteran Soldier"
  ],
  "Faceless One / Vhal, Candlekeep Researcher": [
    "Faceless One",
    "Vhal, Candlekeep Researcher"
  ],
  "Faceless One / Viconia, Drow Apostate": [
    "Faceless One",
    "Viconia, Drow Apostate"
  ],
  "Faceless One / Volo, Itinerant Scholar": [
    "Faceless One",
    "Volo, Itinerant Scholar"
  ],
  "Faceless One / Wilson, Refined Grizzly": [
    "Faceless One",
    "Wilson, Refined Grizzly"
  ],
  "Faceless One / Wyll, Blade of Frontiers": [
    "Faceless One",
    "Wyll, Blade of Frontiers"
  ],
  "Faceless One / Zellix, Sanity Flayer": [
    "Faceless One",
    "Zellix, Sanity Flayer"
  ],
  "Falthis, Shadowcat Familiar / Francisco, Fowl Marauder": [
    "Falthis, Shadowcat Familiar",
    "Francisco, Fowl Marauder"
  ],
  "Falthis, Shadowcat Familiar / Ghost of Ramirez DePietro": [
    "Falthis, Shadowcat Familiar",
    "Ghost of Ramirez DePietro"
  ],
  "Falthis, Shadowcat Familiar / Gilanra, Caller of Wirewood": [
    "Falthis, Shadowcat Familiar",
    "Gilanra, Caller of Wirewood"
  ],
  "Falthis, Shadowcat Familiar / Glacian, Powerstone Engineer": [
    "Falthis, Shadowcat Familiar",
    "Glacian, Powerstone Engineer"
  ],
  "Falthis, Shadowcat Familiar / Halana, Kessig Ranger": [
    "Falthis, Shadowcat Familiar",
    "Halana, Kessig Ranger"
  ],
  "Falthis, Shadowcat Familiar / Ich-Tekik, Salvage Splicer": [
    "Falthis, Shadowcat Familiar",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Falthis, Shadowcat Familiar / Ikra Shidiqi, the Usurper": [
    "Falthis, Shadowcat Familiar",
    "Ikra Shidiqi, the Usurper"
  ],
  "Falthis, Shadowcat Familiar / Ishai, Ojutai Dragonspeaker": [
    "Falthis, Shadowcat Familiar",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Falthis, Shadowcat Familiar / Jeska, Thrice Reborn": [
    "Falthis, Shadowcat Familiar",
    "Jeska, Thrice Reborn"
  ],
  "Falthis, Shadowcat Familiar / Kamahl, Heart of Krosa": [
    "Falthis, Shadowcat Familiar",
    "Kamahl, Heart of Krosa"
  ],
  "Falthis, Shadowcat Familiar / Kediss, Emberclaw Familiar": [
    "Falthis, Shadowcat Familiar",
    "Kediss, Emberclaw Familiar"
  ],
  "Falthis, Shadowcat Familiar / Keleth, Sunmane Familiar": [
    "Falthis, Shadowcat Familiar",
    "Keleth, Sunmane Familiar"
  ],
  "Falthis, Shadowcat Familiar / Keskit, the Flesh Sculptor": [
    "Falthis, Shadowcat Familiar",
    "Keskit, the Flesh Sculptor"
  ],
  "Falthis, Shadowcat Familiar / Kodama of the East Tree": [
    "Falthis, Shadowcat Familiar",
    "Kodama of the East Tree"
  ],
  "Falthis, Shadowcat Familiar / Krark, the Thumbless": [
    "Falthis, Shadowcat Familiar",
    "Krark, the Thumbless"
  ],
  "Falthis, Shadowcat Familiar / Kraum, Ludevic's Opus": [
    "Falthis, Shadowcat Familiar",
    "Kraum, Ludevic's Opus"
  ],
  "Falthis, Shadowcat Familiar / Kydele, Chosen of Kruphix": [
    "Falthis, Shadowcat Familiar",
    "Kydele, Chosen of Kruphix"
  ],
  "Falthis, Shadowcat Familiar / Livio, Oathsworn Sentinel": [
    "Falthis, Shadowcat Familiar",
    "Livio, Oathsworn Sentinel"
  ],
  "Falthis, Shadowcat Familiar / Ludevic, Necro-Alchemist": [
    "Falthis, Shadowcat Familiar",
    "Ludevic, Necro-Alchemist"
  ],
  "Falthis, Shadowcat Familiar / Malcolm, Keen-Eyed Navigator": [
    "Falthis, Shadowcat Familiar",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Falthis, Shadowcat Familiar / Miara, Thorn of the Glade": [
    "Falthis, Shadowcat Familiar",
    "Miara, Thorn of the Glade"
  ],
  "Falthis, Shadowcat Familiar / Nadier, Agent of the Duskenel": [
    "Falthis, Shadowcat Familiar",
    "Nadier, Agent of the Duskenel"
  ],
  "Falthis, Shadowcat Familiar / Numa, Joraga Chieftain": [
    "Falthis, Shadowcat Familiar",
    "Numa, Joraga Chieftain"
  ],
  "Falthis, Shadowcat Familiar / Prava of the Steel Legion": [
    "Falthis, Shadowcat Familiar",
    "Prava of the Steel Legion"
  ],
  "Falthis, Shadowcat Familiar / Radiant, Serra Archangel": [
    "Falthis, Shadowcat Familiar",
    "Radiant, Serra Archangel"
  ],
  "Falthis, Shadowcat Familiar / Ravos, Soultender": [
    "Falthis, Shadowcat Familiar",
    "Ravos, Soultender"
  ],
  "Falthis, Shadowcat Familiar / Rebbec, Architect of Ascension": [
    "Falthis, Shadowcat Familiar",
    "Rebbec, Architect of Ascension"
  ],
  "Falthis, Shadowcat Familiar / Reyhan, Last of the Abzan": [
    "Falthis, Shadowcat Familiar",
    "Reyhan, Last of the Abzan"
  ],
  "Falthis, Shadowcat Familiar / Rograkh, Son of Rohgahh": [
    "Falthis, Shadowcat Familiar",
    "Rograkh, Son of Rohgahh"
  ],
  "Falthis, Shadowcat Familiar / Sakashima of a Thousand Faces": [
    "Falthis, Shadowcat Familiar",
    "Sakashima of a Thousand Faces"
  ],
  "Falthis, Shadowcat Familiar / Sengir, the Dark Baron": [
    "Falthis, Shadowcat Familiar",
    "Sengir, the Dark Baron"
  ],
  "Falthis, Shadowcat Familiar / Siani, Eye of the Storm": [
    "Falthis, Shadowcat Familiar",
    "Siani, Eye of the Storm"
  ],
  "Falthis, Shadowcat Familiar / Sidar Kondo of Jamuraa": [
    "Falthis, Shadowcat Familiar",
    "Sidar Kondo of Jamuraa"
  ],
  "Falthis, Shadowcat Familiar / Silas Renn, Seeker Adept": [
    "Falthis, Shadowcat Familiar",
    "Silas Renn, Seeker Adept"
  ],
  "Falthis, Shadowcat Familiar / Slurrk, All-Ingesting": [
    "Falthis, Shadowcat Familiar",
    "Slurrk, All-Ingesting"
  ],
  "Falthis, Shadowcat Familiar / Tana, the Bloodsower": [
    "Falthis, Shadowcat Familiar",
    "Tana, the Bloodsower"
  ],
  "Falthis, Shadowcat Familiar / Tevesh Szat, Doom of Fools": [
    "Falthis, Shadowcat Familiar",
    "Tevesh Szat, Doom of Fools"
  ],
  "Falthis, Shadowcat Familiar / The Prismatic Piper": [
    "Falthis, Shadowcat Familiar",
    "The Prismatic Piper"
  ],
  "Falthis, Shadowcat Familiar / Thrasios, Triton Hero": [
    "Falthis, Shadowcat Familiar",
    "Thrasios, Triton Hero"
  ],
  "Falthis, Shadowcat Familiar / Toggo, Goblin Weaponsmith": [
    "Falthis, Shadowcat Familiar",
    "Toggo, Goblin Weaponsmith"
  ],
  "Falthis, Shadowcat Familiar / Tormod, the Desecrator": [
    "Falthis, Shadowcat Familiar",
    "Tormod, the Desecrator"
  ],
  "Falthis, Shadowcat Familiar / Tymna the Weaver": [
    "Falthis, Shadowcat Familiar",
    "Tymna the Weaver"
  ],
  "Falthis, Shadowcat Familiar / Vial Smasher the Fierce": [
    "Falthis, Shadowcat Familiar",
    "Vial Smasher the Fierce"
  ],
  "Falthis, Shadowcat Familiar / Yoshimaru, Ever Faithful": [
    "Falthis, Shadowcat Familiar",
    "Yoshimaru, Ever Faithful"
  ],
  "Far Traveler / Gale, Waterdeep Prodigy": [
    "Far Traveler",
    "Gale, Waterdeep Prodigy"
  ],
  "Far Traveler / Ganax, Astral Hunter": [
    "Far Traveler",
    "Ganax, Astral Hunter"
  ],
  "Far Traveler / Gut, True Soul Zealot": [
    "Far Traveler",
    "Gut, True Soul Zealot"
  ],
  "Far Traveler / Halsin, Emerald Archdruid": [
    "Far Traveler",
    "Halsin, Emerald Archdruid"
  ],
  "Far Traveler / Imoen, Mystic Trickster": [
    "Far Traveler",
    "Imoen, Mystic Trickster"
  ],
  "Far Traveler / Jaheira, Friend of the Forest": [
    "Far Traveler",
    "Jaheira, Friend of the Forest"
  ],
  "Far Traveler / Karlach, Fury of Avernus": [
    "Far Traveler",
    "Karlach, Fury of Avernus"
  ],
  "Far Traveler / Lae'zel, Vlaakith's Champion": [
    "Far Traveler",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Far Traveler / Livaan, Cultist of Tiamat": [
    "Far Traveler",
    "Livaan, Cultist of Tiamat"
  ],
  "Far Traveler / Lulu, Loyal Hollyphant": [
    "Far Traveler",
    "Lulu, Loyal Hollyphant"
  ],
  "Far Traveler / Rasaad yn Bashir": [
    "Far Traveler",
    "Rasaad yn Bashir"
  ],
  "Far Traveler / Renari, Merchant of Marvels": [
    "Far Traveler",
    "Renari, Merchant of Marvels"
  ],
  "Far Traveler / Safana, Calimport Cutthroat": [
    "Far Traveler",
    "Safana, Calimport Cutthroat"
  ],
  "Far Traveler / Sarevok, Deathbringer": [
    "Far Traveler",
    "Sarevok, Deathbringer"
  ],
  "Far Traveler / Shadowheart, Dark Justiciar": [
    "Far Traveler",
    "Shadowheart, Dark Justiciar"
  ],
  "Far Traveler / Sivriss, Nightmare Speaker": [
    "Far Traveler",
    "Sivriss, Nightmare Speaker"
  ],
  "Far Traveler / Skanos Dragonheart": [
    "Far Traveler",
    "Skanos Dragonheart"
  ],
  "Far Traveler / Vhal, Candlekeep Researcher": [
    "Far Traveler",
    "Vhal, Candlekeep Researcher"
  ],
  "Far Traveler / Viconia, Drow Apostate": [
    "Far Traveler",
    "Viconia, Drow Apostate"
  ],
  "Far Traveler / Volo, Itinerant Scholar": [
    "Far Traveler",
    "Volo, Itinerant Scholar"
  ],
  "Far Traveler / Wilson, Refined Grizzly": [
    "Far Traveler",
    "Wilson, Refined Grizzly"
  ],
  "Far Traveler / Wyll, Blade of Frontiers": [
    "Far Traveler",
    "Wyll, Blade of Frontiers"
  ],
  "Far Traveler / Zellix, Sanity Flayer": [
    "Far Traveler",
    "Zellix, Sanity Flayer"
  ],
  "Feywild Visitor / Gale, Waterdeep Prodigy": [
    "Feywild Visitor",
    "Gale, Waterdeep Prodigy"
  ],
  "Feywild Visitor / Ganax, Astral Hunter": [
    "Feywild Visitor",
    "Ganax, Astral Hunter"
  ],
  "Feywild Visitor / Gut, True Soul Zealot": [
    "Feywild Visitor",
    "Gut, True Soul Zealot"
  ],
  "Feywild Visitor / Halsin, Emerald Archdruid": [
    "Feywild Visitor",
    "Halsin, Emerald Archdruid"
  ],
  "Feywild Visitor / Imoen, Mystic Trickster": [
    "Feywild Visitor",
    "Imoen, Mystic Trickster"
  ],
  "Feywild Visitor / Jaheira, Friend of the Forest": [
    "Feywild Visitor",
    "Jaheira, Friend of the Forest"
  ],
  "Feywild Visitor / Karlach, Fury of Avernus": [
    "Feywild Visitor",
    "Karlach, Fury of Avernus"
  ],
  "Feywild Visitor / Lae'zel, Vlaakith's Champion": [
    "Feywild Visitor",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Feywild Visitor / Livaan, Cultist of Tiamat": [
    "Feywild Visitor",
    "Livaan, Cultist of Tiamat"
  ],
  "Feywild Visitor / Lulu, Loyal Hollyphant": [
    "Feywild Visitor",
    "Lulu, Loyal Hollyphant"
  ],
  "Feywild Visitor / Rasaad yn Bashir": [
    "Feywild Visitor",
    "Rasaad yn Bashir"
  ],
  "Feywild Visitor / Renari, Merchant of Marvels": [
    "Feywild Visitor",
    "Renari, Merchant of Marvels"
  ],
  "Feywild Visitor / Safana, Calimport Cutthroat": [
    "Feywild Visitor",
    "Safana, Calimport Cutthroat"
  ],
  "Feywild Visitor / Sarevok, Deathbringer": [
    "Feywild Visitor",
    "Sarevok, Deathbringer"
  ],
  "Feywild Visitor / Shadowheart, Dark Justiciar": [
    "Feywild Visitor",
    "Shadowheart, Dark Justiciar"
  ],
  "Feywild Visitor / Sivriss, Nightmare Speaker": [
    "Feywild Visitor",
    "Sivriss, Nightmare Speaker"
  ],
  "Feywild Visitor / Skanos Dragonheart": [
    "Feywild Visitor",
    "Skanos Dragonheart"
  ],
  "Feywild Visitor / Vhal, Candlekeep Researcher": [
    "Feywild Visitor",
    "Vhal, Candlekeep Researcher"
  ],
  "Feywild Visitor / Viconia, Drow Apostate": [
    "Feywild Visitor",
    "Viconia, Drow Apostate"
  ],
  "Feywild Visitor / Volo, Itinerant Scholar": [
    "Feywild Visitor",
    "Volo, Itinerant Scholar"
  ],
  "Feywild Visitor / Wilson, Refined Grizzly": [
    "Feywild Visitor",
    "Wilson, Refined Grizzly"
  ],
  "Feywild Visitor / Wyll, Blade of Frontiers": [
    "Feywild Visitor",
    "Wyll, Blade of Frontiers"
  ],
  "Feywild Visitor / Zellix, Sanity Flayer": [
    "Feywild Visitor",
    "Zellix, Sanity Flayer"
  ],
  "Flaming Fist / Gale, Waterdeep Prodigy": [
    "Flaming Fist",
    "Gale, Waterdeep Prodigy"
  ],
  "Flaming Fist / Ganax, Astral Hunter": [
    "Flaming Fist",
    "Ganax, Astral Hunter"
  ],
  "Flaming Fist / Gut, True Soul Zealot": [
    "Flaming Fist",
    "Gut, True Soul Zealot"
  ],
  "Flaming Fist / Halsin, Emerald Archdruid": [
    "Flaming Fist",
    "Halsin, Emerald Archdruid"
  ],
  "Flaming Fist / Imoen, Mystic Trickster": [
    "Flaming Fist",
    "Imoen, Mystic Trickster"
  ],
  "Flaming Fist / Jaheira, Friend of the Forest": [
    "Flaming Fist",
    "Jaheira, Friend of the Forest"
  ],
  "Flaming Fist / Karlach, Fury of Avernus": [
    "Flaming Fist",
    "Karlach, Fury of Avernus"
  ],
  "Flaming Fist / Lae'zel, Vlaakith's Champion": [
    "Flaming Fist",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Flaming Fist / Livaan, Cultist of Tiamat": [
    "Flaming Fist",
    "Livaan, Cultist of Tiamat"
  ],
  "Flaming Fist / Lulu, Loyal Hollyphant": [
    "Flaming Fist",
    "Lulu, Loyal Hollyphant"
  ],
  "Flaming Fist / Rasaad yn Bashir": [
    "Flaming Fist",
    "Rasaad yn Bashir"
  ],
  "Flaming Fist / Renari, Merchant of Marvels": [
    "Flaming Fist",
    "Renari, Merchant of Marvels"
  ],
  "Flaming Fist / Safana, Calimport Cutthroat": [
    "Flaming Fist",
    "Safana, Calimport Cutthroat"
  ],
  "Flaming Fist / Sarevok, Deathbringer": [
    "Flaming Fist",
    "Sarevok, Deathbringer"
  ],
  "Flaming Fist / Shadowheart, Dark Justiciar": [
    "Flaming Fist",
    "Shadowheart, Dark Justiciar"
  ],
  "Flaming Fist / Sivriss, Nightmare Speaker": [
    "Flaming Fist",
    "Sivriss, Nightmare Speaker"
  ],
  "Flaming Fist / Skanos Dragonheart": [
    "Flaming Fist",
    "Skanos Dragonheart"
  ],
  "Flaming Fist / Vhal, Candlekeep Researcher": [
    "Flaming Fist",
    "Vhal, Candlekeep Researcher"
  ],
  "Flaming Fist / Viconia, Drow Apostate": [
    "Flaming Fist",
    "Viconia, Drow Apostate"
  ],
  "Flaming Fist / Volo, Itinerant Scholar": [
    "Flaming Fist",
    "Volo, Itinerant Scholar"
  ],
  "Flaming Fist / Wilson, Refined Grizzly": [
    "Flaming Fist",
    "Wilson, Refined Grizzly"
  ],
  "Flaming Fist / Wyll, Blade of Frontiers": [
    "Flaming Fist",
    "Wyll, Blade of Frontiers"
  ],
  "Flaming Fist / Zellix, Sanity Flayer": [
    "Flaming Fist",
    "Zellix, Sanity Flayer"
  ],
  "Folk Hero / Gale, Waterdeep Prodigy": [
    "Folk Hero",
    "Gale, Waterdeep Prodigy"
  ],
  "Folk Hero / Ganax, Astral Hunter": [
    "Folk Hero",
    "Ganax, Astral Hunter"
  ],
  "Folk Hero / Gut, True Soul Zealot": [
    "Folk Hero",
    "Gut, True Soul Zealot"
  ],
  "Folk Hero / Halsin, Emerald Archdruid": [
    "Folk Hero",
    "Halsin, Emerald Archdruid"
  ],
  "Folk Hero / Imoen, Mystic Trickster": [
    "Folk Hero",
    "Imoen, Mystic Trickster"
  ],
  "Folk Hero / Jaheira, Friend of the Forest": [
    "Folk Hero",
    "Jaheira, Friend of the Forest"
  ],
  "Folk Hero / Karlach, Fury of Avernus": [
    "Folk Hero",
    "Karlach, Fury of Avernus"
  ],
  "Folk Hero / Lae'zel, Vlaakith's Champion": [
    "Folk Hero",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Folk Hero / Livaan, Cultist of Tiamat": [
    "Folk Hero",
    "Livaan, Cultist of Tiamat"
  ],
  "Folk Hero / Lulu, Loyal Hollyphant": [
    "Folk Hero",
    "Lulu, Loyal Hollyphant"
  ],
  "Folk Hero / Rasaad yn Bashir": [
    "Folk Hero",
    "Rasaad yn Bashir"
  ],
  "Folk Hero / Renari, Merchant of Marvels": [
    "Folk Hero",
    "Renari, Merchant of Marvels"
  ],
  "Folk Hero / Safana, Calimport Cutthroat": [
    "Folk Hero",
    "Safana, Calimport Cutthroat"
  ],
  "Folk Hero / Sarevok, Deathbringer": [
    "Folk Hero",
    "Sarevok, Deathbringer"
  ],
  "Folk Hero / Shadowheart, Dark Justiciar": [
    "Folk Hero",
    "Shadowheart, Dark Justiciar"
  ],
  "Folk Hero / Sivriss, Nightmare Speaker": [
    "Folk Hero",
    "Sivriss, Nightmare Speaker"
  ],
  "Folk Hero / Skanos Dragonheart": [
    "Folk Hero",
    "Skanos Dragonheart"
  ],
  "Folk Hero / Vhal, Candlekeep Researcher": [
    "Folk Hero",
    "Vhal, Candlekeep Researcher"
  ],
  "Folk Hero / Viconia, Drow Apostate": [
    "Folk Hero",
    "Viconia, Drow Apostate"
  ],
  "Folk Hero / Volo, Itinerant Scholar": [
    "Folk Hero",
    "Volo, Itinerant Scholar"
  ],
  "Folk Hero / Wilson, Refined Grizzly": [
    "Folk Hero",
    "Wilson, Refined Grizzly"
  ],
  "Folk Hero / Wyll, Blade of Frontiers": [
    "Folk Hero",
    "Wyll, Blade of Frontiers"
  ],
  "Folk Hero / Zellix, Sanity Flayer": [
    "Folk Hero",
    "Zellix, Sanity Flayer"
  ],
  "Francisco, Fowl Marauder / Ghost of Ramirez DePietro": [
    "Francisco, Fowl Marauder",
    "Ghost of Ramirez DePietro"
  ],
  "Francisco, Fowl Marauder / Gilanra, Caller of Wirewood": [
    "Francisco, Fowl Marauder",
    "Gilanra, Caller of Wirewood"
  ],
  "Francisco, Fowl Marauder / Glacian, Powerstone Engineer": [
    "Francisco, Fowl Marauder",
    "Glacian, Powerstone Engineer"
  ],
  "Francisco, Fowl Marauder / Halana, Kessig Ranger": [
    "Francisco, Fowl Marauder",
    "Halana, Kessig Ranger"
  ],
  "Francisco, Fowl Marauder / Ich-Tekik, Salvage Splicer": [
    "Francisco, Fowl Marauder",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Francisco, Fowl Marauder / Ikra Shidiqi, the Usurper": [
    "Francisco, Fowl Marauder",
    "Ikra Shidiqi, the Usurper"
  ],
  "Francisco, Fowl Marauder / Ishai, Ojutai Dragonspeaker": [
    "Francisco, Fowl Marauder",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Francisco, Fowl Marauder / Jeska, Thrice Reborn": [
    "Francisco, Fowl Marauder",
    "Jeska, Thrice Reborn"
  ],
  "Francisco, Fowl Marauder / Kamahl, Heart of Krosa": [
    "Francisco, Fowl Marauder",
    "Kamahl, Heart of Krosa"
  ],
  "Francisco, Fowl Marauder / Kediss, Emberclaw Familiar": [
    "Francisco, Fowl Marauder",
    "Kediss, Emberclaw Familiar"
  ],
  "Francisco, Fowl Marauder / Keleth, Sunmane Familiar": [
    "Francisco, Fowl Marauder",
    "Keleth, Sunmane Familiar"
  ],
  "Francisco, Fowl Marauder / Keskit, the Flesh Sculptor": [
    "Francisco, Fowl Marauder",
    "Keskit, the Flesh Sculptor"
  ],
  "Francisco, Fowl Marauder / Kodama of the East Tree": [
    "Francisco, Fowl Marauder",
    "Kodama of the East Tree"
  ],
  "Francisco, Fowl Marauder / Krark, the Thumbless": [
    "Francisco, Fowl Marauder",
    "Krark, the Thumbless"
  ],
  "Francisco, Fowl Marauder / Kraum, Ludevic's Opus": [
    "Francisco, Fowl Marauder",
    "Kraum, Ludevic's Opus"
  ],
  "Francisco, Fowl Marauder / Kydele, Chosen of Kruphix": [
    "Francisco, Fowl Marauder",
    "Kydele, Chosen of Kruphix"
  ],
  "Francisco, Fowl Marauder / Livio, Oathsworn Sentinel": [
    "Francisco, Fowl Marauder",
    "Livio, Oathsworn Sentinel"
  ],
  "Francisco, Fowl Marauder / Ludevic, Necro-Alchemist": [
    "Francisco, Fowl Marauder",
    "Ludevic, Necro-Alchemist"
  ],
  "Francisco, Fowl Marauder / Malcolm, Keen-Eyed Navigator": [
    "Malcolm, Keen-Eyed Navigator",
    "Francisco, Fowl Marauder"
  ],
  "Francisco, Fowl Marauder / Miara, Thorn of the Glade": [
    "Francisco, Fowl Marauder",
    "Miara, Thorn of the Glade"
  ],
  "Francisco, Fowl Marauder / Nadier, Agent of the Duskenel": [
    "Francisco, Fowl Marauder",
    "Nadier, Agent of the Duskenel"
  ],
  "Francisco, Fowl Marauder / Numa, Joraga Chieftain": [
    "Francisco, Fowl Marauder",
    "Numa, Joraga Chieftain"
  ],
  "Francisco, Fowl Marauder / Prava of the Steel Legion": [
    "Francisco, Fowl Marauder",
    "Prava of the Steel Legion"
  ],
  "Francisco, Fowl Marauder / Radiant, Serra Archangel": [
    "Francisco, Fowl Marauder",
    "Radiant, Serra Archangel"
  ],
  "Francisco, Fowl Marauder / Ravos, Soultender": [
    "Francisco, Fowl Marauder",
    "Ravos, Soultender"
  ],
  "Francisco, Fowl Marauder / Rebbec, Architect of Ascension": [
    "Francisco, Fowl Marauder",
    "Rebbec, Architect of Ascension"
  ],
  "Francisco, Fowl Marauder / Reyhan, Last of the Abzan": [
    "Francisco, Fowl Marauder",
    "Reyhan, Last of the Abzan"
  ],
  "Francisco, Fowl Marauder / Rograkh, Son of Rohgahh": [
    "Francisco, Fowl Marauder",
    "Rograkh, Son of Rohgahh"
  ],
  "Francisco, Fowl Marauder / Sakashima of a Thousand Faces": [
    "Francisco, Fowl Marauder",
    "Sakashima of a Thousand Faces"
  ],
  "Francisco, Fowl Marauder / Sengir, the Dark Baron": [
    "Francisco, Fowl Marauder",
    "Sengir, the Dark Baron"
  ],
  "Francisco, Fowl Marauder / Siani, Eye of the Storm": [
    "Francisco, Fowl Marauder",
    "Siani, Eye of the Storm"
  ],
  "Francisco, Fowl Marauder / Sidar Kondo of Jamuraa": [
    "Francisco, Fowl Marauder",
    "Sidar Kondo of Jamuraa"
  ],
  "Francisco, Fowl Marauder / Silas Renn, Seeker Adept": [
    "Francisco, Fowl Marauder",
    "Silas Renn, Seeker Adept"
  ],
  "Francisco, Fowl Marauder / Slurrk, All-Ingesting": [
    "Francisco, Fowl Marauder",
    "Slurrk, All-Ingesting"
  ],
  "Francisco, Fowl Marauder / Tana, the Bloodsower": [
    "Francisco, Fowl Marauder",
    "Tana, the Bloodsower"
  ],
  "Francisco, Fowl Marauder / Tevesh Szat, Doom of Fools": [
    "Francisco, Fowl Marauder",
    "Tevesh Szat, Doom of Fools"
  ],
  "Francisco, Fowl Marauder / The Prismatic Piper": [
    "Francisco, Fowl Marauder",
    "The Prismatic Piper"
  ],
  "Francisco, Fowl Marauder / Thrasios, Triton Hero": [
    "Francisco, Fowl Marauder",
    "Thrasios, Triton Hero"
  ],
  "Francisco, Fowl Marauder / Toggo, Goblin Weaponsmith": [
    "Francisco, Fowl Marauder",
    "Toggo, Goblin Weaponsmith"
  ],
  "Francisco, Fowl Marauder / Tormod, the Desecrator": [
    "Francisco, Fowl Marauder",
    "Tormod, the Desecrator"
  ],
  "Francisco, Fowl Marauder / Tymna the Weaver": [
    "Francisco, Fowl Marauder",
    "Tymna the Weaver"
  ],
  "Francisco, Fowl Marauder / Vial Smasher the Fierce": [
    "Francisco, Fowl Marauder",
    "Vial Smasher the Fierce"
  ],
  "Francisco, Fowl Marauder / Yoshimaru, Ever Faithful": [
    "Francisco, Fowl Marauder",
    "Yoshimaru, Ever Faithful"
  ],
  "Frodo, Adventurous Hobbit / Sam, Loyal Attendant": [
    "Frodo, Adventurous Hobbit",
    "Sam, Loyal Attendant"
  ],
  "Gale, Waterdeep Prodigy / Guild Artisan": [
    "Gale, Waterdeep Prodigy",
    "Guild Artisan"
  ],
  "Gale, Waterdeep Prodigy / Hardy Outlander": [
    "Gale, Waterdeep Prodigy",
    "Hardy Outlander"
  ],
  "Gale, Waterdeep Prodigy / Haunted One": [
    "Gale, Waterdeep Prodigy",
    "Haunted One"
  ],
  "Gale, Waterdeep Prodigy / Inspiring Leader": [
    "Gale, Waterdeep Prodigy",
    "Inspiring Leader"
  ],
  "Gale, Waterdeep Prodigy / Master Chef": [
    "Gale, Waterdeep Prodigy",
    "Master Chef"
  ],
  "Gale, Waterdeep Prodigy / Noble Heritage": [
    "Gale, Waterdeep Prodigy",
    "Noble Heritage"
  ],
  "Gale, Waterdeep Prodigy / Passionate Archaeologist": [
    "Gale, Waterdeep Prodigy",
    "Passionate Archaeologist"
  ],
  "Gale, Waterdeep Prodigy / Popular Entertainer": [
    "Gale, Waterdeep Prodigy",
    "Popular Entertainer"
  ],
  "Gale, Waterdeep Prodigy / Raised by Giants": [
    "Gale, Waterdeep Prodigy",
    "Raised by Giants"
  ],
  "Gale, Waterdeep Prodigy / Scion of Halaster": [
    "Gale, Waterdeep Prodigy",
    "Scion of Halaster"
  ],
  "Gale, Waterdeep Prodigy / Shameless Charlatan": [
    "Gale, Waterdeep Prodigy",
    "Shameless Charlatan"
  ],
  "Gale, Waterdeep Prodigy / Street Urchin": [
    "Gale, Waterdeep Prodigy",
    "Street Urchin"
  ],
  "Gale, Waterdeep Prodigy / Sword Coast Sailor": [
    "Gale, Waterdeep Prodigy",
    "Sword Coast Sailor"
  ],
  "Gale, Waterdeep Prodigy / Tavern Brawler": [
    "Gale, Waterdeep Prodigy",
    "Tavern Brawler"
  ],
  "Gale, Waterdeep Prodigy / Veteran Soldier": [
    "Gale, Waterdeep Prodigy",
    "Veteran Soldier"
  ],
  "Ganax, Astral Hunter / Guild Artisan": [
    "Ganax, Astral Hunter",
    "Guild Artisan"
  ],
  "Ganax, Astral Hunter / Hardy Outlander": [
    "Ganax, Astral Hunter",
    "Hardy Outlander"
  ],
  "Ganax, Astral Hunter / Haunted One": [
    "Ganax, Astral Hunter",
    "Haunted One"
  ],
  "Ganax, Astral Hunter / Inspiring Leader": [
    "Ganax, Astral Hunter",
    "Inspiring Leader"
  ],
  "Ganax, Astral Hunter / Master Chef": [
    "Ganax, Astral Hunter",
    "Master Chef"
  ],
  "Ganax, Astral Hunter / Noble Heritage": [
    "Ganax, Astral Hunter",
    "Noble Heritage"
  ],
  "Ganax, Astral Hunter / Passionate Archaeologist": [
    "Ganax, Astral Hunter",
    "Passionate Archaeologist"
  ],
  "Ganax, Astral Hunter / Popular Entertainer": [
    "Ganax, Astral Hunter",
    "Popular Entertainer"
  ],
  "Ganax, Astral Hunter / Raised by Giants": [
    "Ganax, Astral Hunter",
    "Raised by Giants"
  ],
  "Ganax, Astral Hunter / Scion of Halaster": [
    "Ganax, Astral Hunter",
    "Scion of Halaster"
  ],
  "Ganax, Astral Hunter / Shameless Charlatan": [
    "Ganax, Astral Hunter",
    "Shameless Charlatan"
  ],
  "Ganax, Astral Hunter / Street Urchin": [
    "Ganax, Astral Hunter",
    "Street Urchin"
  ],
  "Ganax, Astral Hunter / Sword Coast Sailor": [
    "Ganax, Astral Hunter",
    "Sword Coast Sailor"
  ],
  "Ganax, Astral Hunter / Tavern Brawler": [
    "Ganax, Astral Hunter",
    "Tavern Brawler"
  ],
  "Ganax, Astral Hunter / Veteran Soldier": [
    "Ganax, Astral Hunter",
    "Veteran Soldier"
  ],
  "Ghost of Ramirez DePietro / Gilanra, Caller of Wirewood": [
    "Ghost of Ramirez DePietro",
    "Gilanra, Caller of Wirewood"
  ],
  "Ghost of Ramirez DePietro / Glacian, Powerstone Engineer": [
    "Ghost of Ramirez DePietro",
    "Glacian, Powerstone Engineer"
  ],
  "Ghost of Ramirez DePietro / Halana, Kessig Ranger": [
    "Ghost of Ramirez DePietro",
    "Halana, Kessig Ranger"
  ],
  "Ghost of Ramirez DePietro / Ich-Tekik, Salvage Splicer": [
    "Ghost of Ramirez DePietro",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Ghost of Ramirez DePietro / Ikra Shidiqi, the Usurper": [
    "Ghost of Ramirez DePietro",
    "Ikra Shidiqi, the Usurper"
  ],
  "Ghost of Ramirez DePietro / Ishai, Ojutai Dragonspeaker": [
    "Ghost of Ramirez DePietro",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ghost of Ramirez DePietro / Jeska, Thrice Reborn": [
    "Ghost of Ramirez DePietro",
    "Jeska, Thrice Reborn"
  ],
  "Ghost of Ramirez DePietro / Kamahl, Heart of Krosa": [
    "Ghost of Ramirez DePietro",
    "Kamahl, Heart of Krosa"
  ],
  "Ghost of Ramirez DePietro / Kediss, Emberclaw Familiar": [
    "Ghost of Ramirez DePietro",
    "Kediss, Emberclaw Familiar"
  ],
  "Ghost of Ramirez DePietro / Keleth, Sunmane Familiar": [
    "Ghost of Ramirez DePietro",
    "Keleth, Sunmane Familiar"
  ],
  "Ghost of Ramirez DePietro / Keskit, the Flesh Sculptor": [
    "Ghost of Ramirez DePietro",
    "Keskit, the Flesh Sculptor"
  ],
  "Ghost of Ramirez DePietro / Kodama of the East Tree": [
    "Ghost of Ramirez DePietro",
    "Kodama of the East Tree"
  ],
  "Ghost of Ramirez DePietro / Krark, the Thumbless": [
    "Ghost of Ramirez DePietro",
    "Krark, the Thumbless"
  ],
  "Ghost of Ramirez DePietro / Kraum, Ludevic's Opus": [
    "Ghost of Ramirez DePietro",
    "Kraum, Ludevic's Opus"
  ],
  "Ghost of Ramirez DePietro / Kydele, Chosen of Kruphix": [
    "Ghost of Ramirez DePietro",
    "Kydele, Chosen of Kruphix"
  ],
  "Ghost of Ramirez DePietro / Livio, Oathsworn Sentinel": [
    "Ghost of Ramirez DePietro",
    "Livio, Oathsworn Sentinel"
  ],
  "Ghost of Ramirez DePietro / Ludevic, Necro-Alchemist": [
    "Ghost of Ramirez DePietro",
    "Ludevic, Necro-Alchemist"
  ],
  "Ghost of Ramirez DePietro / Malcolm, Keen-Eyed Navigator": [
    "Ghost of Ramirez DePietro",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ghost of Ramirez DePietro / Miara, Thorn of the Glade": [
    "Ghost of Ramirez DePietro",
    "Miara, Thorn of the Glade"
  ],
  "Ghost of Ramirez DePietro / Nadier, Agent of the Duskenel": [
    "Ghost of Ramirez DePietro",
    "Nadier, Agent of the Duskenel"
  ],
  "Ghost of Ramirez DePietro / Numa, Joraga Chieftain": [
    "Ghost of Ramirez DePietro",
    "Numa, Joraga Chieftain"
  ],
  "Ghost of Ramirez DePietro / Prava of the Steel Legion": [
    "Ghost of Ramirez DePietro",
    "Prava of the Steel Legion"
  ],
  "Ghost of Ramirez DePietro / Radiant, Serra Archangel": [
    "Ghost of Ramirez DePietro",
    "Radiant, Serra Archangel"
  ],
  "Ghost of Ramirez DePietro / Ravos, Soultender": [
    "Ghost of Ramirez DePietro",
    "Ravos, Soultender"
  ],
  "Ghost of Ramirez DePietro / Rebbec, Architect of Ascension": [
    "Ghost of Ramirez DePietro",
    "Rebbec, Architect of Ascension"
  ],
  "Ghost of Ramirez DePietro / Reyhan, Last of the Abzan": [
    "Ghost of Ramirez DePietro",
    "Reyhan, Last of the Abzan"
  ],
  "Ghost of Ramirez DePietro / Rograkh, Son of Rohgahh": [
    "Ghost of Ramirez DePietro",
    "Rograkh, Son of Rohgahh"
  ],
  "Ghost of Ramirez DePietro / Sakashima of a Thousand Faces": [
    "Ghost of Ramirez DePietro",
    "Sakashima of a Thousand Faces"
  ],
  "Ghost of Ramirez DePietro / Sengir, the Dark Baron": [
    "Ghost of Ramirez DePietro",
    "Sengir, the Dark Baron"
  ],
  "Ghost of Ramirez DePietro / Siani, Eye of the Storm": [
    "Ghost of Ramirez DePietro",
    "Siani, Eye of the Storm"
  ],
  "Ghost of Ramirez DePietro / Sidar Kondo of Jamuraa": [
    "Ghost of Ramirez DePietro",
    "Sidar Kondo of Jamuraa"
  ],
  "Ghost of Ramirez DePietro / Silas Renn, Seeker Adept": [
    "Ghost of Ramirez DePietro",
    "Silas Renn, Seeker Adept"
  ],
  "Ghost of Ramirez DePietro / Slurrk, All-Ingesting": [
    "Ghost of Ramirez DePietro",
    "Slurrk, All-Ingesting"
  ],
  "Ghost of Ramirez DePietro / Tana, the Bloodsower": [
    "Ghost of Ramirez DePietro",
    "Tana, the Bloodsower"
  ],
  "Ghost of Ramirez DePietro / Tevesh Szat, Doom of Fools": [
    "Ghost of Ramirez DePietro",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ghost of Ramirez DePietro / The Prismatic Piper": [
    "Ghost of Ramirez DePietro",
    "The Prismatic Piper"
  ],
  "Ghost of Ramirez DePietro / Thrasios, Triton Hero": [
    "Ghost of Ramirez DePietro",
    "Thrasios, Triton Hero"
  ],
  "Ghost of Ramirez DePietro / Toggo, Goblin Weaponsmith": [
    "Ghost of Ramirez DePietro",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ghost of Ramirez DePietro / Tormod, the Desecrator": [
    "Ghost of Ramirez DePietro",
    "Tormod, the Desecrator"
  ],
  "Ghost of Ramirez DePietro / Tymna the Weaver": [
    "Ghost of Ramirez DePietro",
    "Tymna the Weaver"
  ],
  "Ghost of Ramirez DePietro / Vial Smasher the Fierce": [
    "Ghost of Ramirez DePietro",
    "Vial Smasher the Fierce"
  ],
  "Ghost of Ramirez DePietro / Yoshimaru, Ever Faithful": [
    "Ghost of Ramirez DePietro",
    "Yoshimaru, Ever Faithful"
  ],
  "Gilanra, Caller of Wirewood / Glacian, Powerstone Engineer": [
    "Gilanra, Caller of Wirewood",
    "Glacian, Powerstone Engineer"
  ],
  "Gilanra, Caller of Wirewood / Halana, Kessig Ranger": [
    "Gilanra, Caller of Wirewood",
    "Halana, Kessig Ranger"
  ],
  "Gilanra, Caller of Wirewood / Ich-Tekik, Salvage Splicer": [
    "Gilanra, Caller of Wirewood",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Gilanra, Caller of Wirewood / Ikra Shidiqi, the Usurper": [
    "Gilanra, Caller of Wirewood",
    "Ikra Shidiqi, the Usurper"
  ],
  "Gilanra, Caller of Wirewood / Ishai, Ojutai Dragonspeaker": [
    "Gilanra, Caller of Wirewood",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Gilanra, Caller of Wirewood / Jeska, Thrice Reborn": [
    "Gilanra, Caller of Wirewood",
    "Jeska, Thrice Reborn"
  ],
  "Gilanra, Caller of Wirewood / Kamahl, Heart of Krosa": [
    "Gilanra, Caller of Wirewood",
    "Kamahl, Heart of Krosa"
  ],
  "Gilanra, Caller of Wirewood / Kediss, Emberclaw Familiar": [
    "Gilanra, Caller of Wirewood",
    "Kediss, Emberclaw Familiar"
  ],
  "Gilanra, Caller of Wirewood / Keleth, Sunmane Familiar": [
    "Gilanra, Caller of Wirewood",
    "Keleth, Sunmane Familiar"
  ],
  "Gilanra, Caller of Wirewood / Keskit, the Flesh Sculptor": [
    "Gilanra, Caller of Wirewood",
    "Keskit, the Flesh Sculptor"
  ],
  "Gilanra, Caller of Wirewood / Kodama of the East Tree": [
    "Gilanra, Caller of Wirewood",
    "Kodama of the East Tree"
  ],
  "Gilanra, Caller of Wirewood / Krark, the Thumbless": [
    "Gilanra, Caller of Wirewood",
    "Krark, the Thumbless"
  ],
  "Gilanra, Caller of Wirewood / Kraum, Ludevic's Opus": [
    "Gilanra, Caller of Wirewood",
    "Kraum, Ludevic's Opus"
  ],
  "Gilanra, Caller of Wirewood / Kydele, Chosen of Kruphix": [
    "Gilanra, Caller of Wirewood",
    "Kydele, Chosen of Kruphix"
  ],
  "Gilanra, Caller of Wirewood / Livio, Oathsworn Sentinel": [
    "Gilanra, Caller of Wirewood",
    "Livio, Oathsworn Sentinel"
  ],
  "Gilanra, Caller of Wirewood / Ludevic, Necro-Alchemist": [
    "Gilanra, Caller of Wirewood",
    "Ludevic, Necro-Alchemist"
  ],
  "Gilanra, Caller of Wirewood / Malcolm, Keen-Eyed Navigator": [
    "Gilanra, Caller of Wirewood",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Gilanra, Caller of Wirewood / Miara, Thorn of the Glade": [
    "Gilanra, Caller of Wirewood",
    "Miara, Thorn of the Glade"
  ],
  "Gilanra, Caller of Wirewood / Nadier, Agent of the Duskenel": [
    "Gilanra, Caller of Wirewood",
    "Nadier, Agent of the Duskenel"
  ],
  "Gilanra, Caller of Wirewood / Numa, Joraga Chieftain": [
    "Gilanra, Caller of Wirewood",
    "Numa, Joraga Chieftain"
  ],
  "Gilanra, Caller of Wirewood / Prava of the Steel Legion": [
    "Gilanra, Caller of Wirewood",
    "Prava of the Steel Legion"
  ],
  "Gilanra, Caller of Wirewood / Radiant, Serra Archangel": [
    "Gilanra, Caller of Wirewood",
    "Radiant, Serra Archangel"
  ],
  "Gilanra, Caller of Wirewood / Ravos, Soultender": [
    "Gilanra, Caller of Wirewood",
    "Ravos, Soultender"
  ],
  "Gilanra, Caller of Wirewood / Rebbec, Architect of Ascension": [
    "Gilanra, Caller of Wirewood",
    "Rebbec, Architect of Ascension"
  ],
  "Gilanra, Caller of Wirewood / Reyhan, Last of the Abzan": [
    "Gilanra, Caller of Wirewood",
    "Reyhan, Last of the Abzan"
  ],
  "Gilanra, Caller of Wirewood / Rograkh, Son of Rohgahh": [
    "Gilanra, Caller of Wirewood",
    "Rograkh, Son of Rohgahh"
  ],
  "Gilanra, Caller of Wirewood / Sakashima of a Thousand Faces": [
    "Gilanra, Caller of Wirewood",
    "Sakashima of a Thousand Faces"
  ],
  "Gilanra, Caller of Wirewood / Sengir, the Dark Baron": [
    "Gilanra, Caller of Wirewood",
    "Sengir, the Dark Baron"
  ],
  "Gilanra, Caller of Wirewood / Siani, Eye of the Storm": [
    "Gilanra, Caller of Wirewood",
    "Siani, Eye of the Storm"
  ],
  "Gilanra, Caller of Wirewood / Sidar Kondo of Jamuraa": [
    "Gilanra, Caller of Wirewood",
    "Sidar Kondo of Jamuraa"
  ],
  "Gilanra, Caller of Wirewood / Silas Renn, Seeker Adept": [
    "Gilanra, Caller of Wirewood",
    "Silas Renn, Seeker Adept"
  ],
  "Gilanra, Caller of Wirewood / Slurrk, All-Ingesting": [
    "Gilanra, Caller of Wirewood",
    "Slurrk, All-Ingesting"
  ],
  "Gilanra, Caller of Wirewood / Tana, the Bloodsower": [
    "Gilanra, Caller of Wirewood",
    "Tana, the Bloodsower"
  ],
  "Gilanra, Caller of Wirewood / Tevesh Szat, Doom of Fools": [
    "Gilanra, Caller of Wirewood",
    "Tevesh Szat, Doom of Fools"
  ],
  "Gilanra, Caller of Wirewood / The Prismatic Piper": [
    "Gilanra, Caller of Wirewood",
    "The Prismatic Piper"
  ],
  "Gilanra, Caller of Wirewood / Thrasios, Triton Hero": [
    "Gilanra, Caller of Wirewood",
    "Thrasios, Triton Hero"
  ],
  "Gilanra, Caller of Wirewood / Toggo, Goblin Weaponsmith": [
    "Gilanra, Caller of Wirewood",
    "Toggo, Goblin Weaponsmith"
  ],
  "Gilanra, Caller of Wirewood / Tormod, the Desecrator": [
    "Gilanra, Caller of Wirewood",
    "Tormod, the Desecrator"
  ],
  "Gilanra, Caller of Wirewood / Tymna the Weaver": [
    "Gilanra, Caller of Wirewood",
    "Tymna the Weaver"
  ],
  "Gilanra, Caller of Wirewood / Vial Smasher the Fierce": [
    "Gilanra, Caller of Wirewood",
    "Vial Smasher the Fierce"
  ],
  "Gilanra, Caller of Wirewood / Yoshimaru, Ever Faithful": [
    "Gilanra, Caller of Wirewood",
    "Yoshimaru, Ever Faithful"
  ],
  "Glacian, Powerstone Engineer / Halana, Kessig Ranger": [
    "Glacian, Powerstone Engineer",
    "Halana, Kessig Ranger"
  ],
  "Glacian, Powerstone Engineer / Ich-Tekik, Salvage Splicer": [
    "Glacian, Powerstone Engineer",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Glacian, Powerstone Engineer / Ikra Shidiqi, the Usurper": [
    "Glacian, Powerstone Engineer",
    "Ikra Shidiqi, the Usurper"
  ],
  "Glacian, Powerstone Engineer / Ishai, Ojutai Dragonspeaker": [
    "Glacian, Powerstone Engineer",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Glacian, Powerstone Engineer / Jeska, Thrice Reborn": [
    "Glacian, Powerstone Engineer",
    "Jeska, Thrice Reborn"
  ],
  "Glacian, Powerstone Engineer / Kamahl, Heart of Krosa": [
    "Glacian, Powerstone Engineer",
    "Kamahl, Heart of Krosa"
  ],
  "Glacian, Powerstone Engineer / Kediss, Emberclaw Familiar": [
    "Glacian, Powerstone Engineer",
    "Kediss, Emberclaw Familiar"
  ],
  "Glacian, Powerstone Engineer / Keleth, Sunmane Familiar": [
    "Glacian, Powerstone Engineer",
    "Keleth, Sunmane Familiar"
  ],
  "Glacian, Powerstone Engineer / Keskit, the Flesh Sculptor": [
    "Glacian, Powerstone Engineer",
    "Keskit, the Flesh Sculptor"
  ],
  "Glacian, Powerstone Engineer / Kodama of the East Tree": [
    "Glacian, Powerstone Engineer",
    "Kodama of the East Tree"
  ],
  "Glacian, Powerstone Engineer / Krark, the Thumbless": [
    "Glacian, Powerstone Engineer",
    "Krark, the Thumbless"
  ],
  "Glacian, Powerstone Engineer / Kraum, Ludevic's Opus": [
    "Glacian, Powerstone Engineer",
    "Kraum, Ludevic's Opus"
  ],
  "Glacian, Powerstone Engineer / Kydele, Chosen of Kruphix": [
    "Glacian, Powerstone Engineer",
    "Kydele, Chosen of Kruphix"
  ],
  "Glacian, Powerstone Engineer / Livio, Oathsworn Sentinel": [
    "Glacian, Powerstone Engineer",
    "Livio, Oathsworn Sentinel"
  ],
  "Glacian, Powerstone Engineer / Ludevic, Necro-Alchemist": [
    "Glacian, Powerstone Engineer",
    "Ludevic, Necro-Alchemist"
  ],
  "Glacian, Powerstone Engineer / Malcolm, Keen-Eyed Navigator": [
    "Glacian, Powerstone Engineer",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Glacian, Powerstone Engineer / Miara, Thorn of the Glade": [
    "Glacian, Powerstone Engineer",
    "Miara, Thorn of the Glade"
  ],
  "Glacian, Powerstone Engineer / Nadier, Agent of the Duskenel": [
    "Glacian, Powerstone Engineer",
    "Nadier, Agent of the Duskenel"
  ],
  "Glacian, Powerstone Engineer / Numa, Joraga Chieftain": [
    "Glacian, Powerstone Engineer",
    "Numa, Joraga Chieftain"
  ],
  "Glacian, Powerstone Engineer / Prava of the Steel Legion": [
    "Glacian, Powerstone Engineer",
    "Prava of the Steel Legion"
  ],
  "Glacian, Powerstone Engineer / Radiant, Serra Archangel": [
    "Glacian, Powerstone Engineer",
    "Radiant, Serra Archangel"
  ],
  "Glacian, Powerstone Engineer / Ravos, Soultender": [
    "Glacian, Powerstone Engineer",
    "Ravos, Soultender"
  ],
  "Glacian, Powerstone Engineer / Rebbec, Architect of Ascension": [
    "Glacian, Powerstone Engineer",
    "Rebbec, Architect of Ascension"
  ],
  "Glacian, Powerstone Engineer / Reyhan, Last of the Abzan": [
    "Glacian, Powerstone Engineer",
    "Reyhan, Last of the Abzan"
  ],
  "Glacian, Powerstone Engineer / Rograkh, Son of Rohgahh": [
    "Glacian, Powerstone Engineer",
    "Rograkh, Son of Rohgahh"
  ],
  "Glacian, Powerstone Engineer / Sakashima of a Thousand Faces": [
    "Glacian, Powerstone Engineer",
    "Sakashima of a Thousand Faces"
  ],
  "Glacian, Powerstone Engineer / Sengir, the Dark Baron": [
    "Glacian, Powerstone Engineer",
    "Sengir, the Dark Baron"
  ],
  "Glacian, Powerstone Engineer / Siani, Eye of the Storm": [
    "Glacian, Powerstone Engineer",
    "Siani, Eye of the Storm"
  ],
  "Glacian, Powerstone Engineer / Sidar Kondo of Jamuraa": [
    "Glacian, Powerstone Engineer",
    "Sidar Kondo of Jamuraa"
  ],
  "Glacian, Powerstone Engineer / Silas Renn, Seeker Adept": [
    "Glacian, Powerstone Engineer",
    "Silas Renn, Seeker Adept"
  ],
  "Glacian, Powerstone Engineer / Slurrk, All-Ingesting": [
    "Glacian, Powerstone Engineer",
    "Slurrk, All-Ingesting"
  ],
  "Glacian, Powerstone Engineer / Tana, the Bloodsower": [
    "Glacian, Powerstone Engineer",
    "Tana, the Bloodsower"
  ],
  "Glacian, Powerstone Engineer / Tevesh Szat, Doom of Fools": [
    "Glacian, Powerstone Engineer",
    "Tevesh Szat, Doom of Fools"
  ],
  "Glacian, Powerstone Engineer / The Prismatic Piper": [
    "Glacian, Powerstone Engineer",
    "The Prismatic Piper"
  ],
  "Glacian, Powerstone Engineer / Thrasios, Triton Hero": [
    "Glacian, Powerstone Engineer",
    "Thrasios, Triton Hero"
  ],
  "Glacian, Powerstone Engineer / Toggo, Goblin Weaponsmith": [
    "Glacian, Powerstone Engineer",
    "Toggo, Goblin Weaponsmith"
  ],
  "Glacian, Powerstone Engineer / Tormod, the Desecrator": [
    "Glacian, Powerstone Engineer",
    "Tormod, the Desecrator"
  ],
  "Glacian, Powerstone Engineer / Tymna the Weaver": [
    "Glacian, Powerstone Engineer",
    "Tymna the Weaver"
  ],
  "Glacian, Powerstone Engineer / Vial Smasher the Fierce": [
    "Glacian, Powerstone Engineer",
    "Vial Smasher the Fierce"
  ],
  "Glacian, Powerstone Engineer / Yoshimaru, Ever Faithful": [
    "Glacian, Powerstone Engineer",
    "Yoshimaru, Ever Faithful"
  ],
  "Gorm the Great / Virtus the Veiled": [
    "Gorm the Great",
    "Virtus the Veiled"
  ],
  "Graham O'Brien / The Eighth Doctor": [
    "Graham O'Brien",
    "The Eighth Doctor"
  ],
  "Graham O'Brien / The Eleventh Doctor": [
    "Graham O'Brien",
    "The Eleventh Doctor"
  ],
  "Graham O'Brien / The Fifteenth Doctor": [
    "Graham O'Brien",
    "The Fifteenth Doctor"
  ],
  "Graham O'Brien / The Fifth Doctor": [
    "Graham O'Brien",
    "The Fifth Doctor"
  ],
  "Graham O'Brien / The First Doctor": [
    "Graham O'Brien",
    "The First Doctor"
  ],
  "Graham O'Brien / The Fourteenth Doctor": [
    "Graham O'Brien",
    "The Fourteenth Doctor"
  ],
  "Graham O'Brien / The Fourth Doctor": [
    "Graham O'Brien",
    "The Fourth Doctor"
  ],
  "Graham O'Brien / The Fugitive Doctor": [
    "Graham O'Brien",
    "The Fugitive Doctor"
  ],
  "Graham O'Brien / The Ninth Doctor": [
    "Graham O'Brien",
    "The Ninth Doctor"
  ],
  "Graham O'Brien / The Second Doctor": [
    "Graham O'Brien",
    "The Second Doctor"
  ],
  "Graham O'Brien / The Seventh Doctor": [
    "Graham O'Brien",
    "The Seventh Doctor"
  ],
  "Graham O'Brien / The Sixth Doctor": [
    "Graham O'Brien",
    "The Sixth Doctor"
  ],
  "Graham O'Brien / The Tenth Doctor": [
    "Graham O'Brien",
    "The Tenth Doctor"
  ],
  "Graham O'Brien / The Third Doctor": [
    "Graham O'Brien",
    "The Third Doctor"
  ],
  "Graham O'Brien / The Thirteenth Doctor": [
    "Graham O'Brien",
    "The Thirteenth Doctor"
  ],
  "Graham O'Brien / The Twelfth Doctor": [
    "Graham O'Brien",
    "The Twelfth Doctor"
  ],
  "Graham O'Brien / The War Doctor": [
    "Graham O'Brien",
    "The War Doctor"
  ],
  "Guild Artisan / Gut, True Soul Zealot": [
    "Guild Artisan",
    "Gut, True Soul Zealot"
  ],
  "Guild Artisan / Halsin, Emerald Archdruid": [
    "Guild Artisan",
    "Halsin, Emerald Archdruid"
  ],
  "Guild Artisan / Imoen, Mystic Trickster": [
    "Guild Artisan",
    "Imoen, Mystic Trickster"
  ],
  "Guild Artisan / Jaheira, Friend of the Forest": [
    "Guild Artisan",
    "Jaheira, Friend of the Forest"
  ],
  "Guild Artisan / Karlach, Fury of Avernus": [
    "Guild Artisan",
    "Karlach, Fury of Avernus"
  ],
  "Guild Artisan / Lae'zel, Vlaakith's Champion": [
    "Guild Artisan",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Guild Artisan / Livaan, Cultist of Tiamat": [
    "Guild Artisan",
    "Livaan, Cultist of Tiamat"
  ],
  "Guild Artisan / Lulu, Loyal Hollyphant": [
    "Guild Artisan",
    "Lulu, Loyal Hollyphant"
  ],
  "Guild Artisan / Rasaad yn Bashir": [
    "Guild Artisan",
    "Rasaad yn Bashir"
  ],
  "Guild Artisan / Renari, Merchant of Marvels": [
    "Guild Artisan",
    "Renari, Merchant of Marvels"
  ],
  "Guild Artisan / Safana, Calimport Cutthroat": [
    "Guild Artisan",
    "Safana, Calimport Cutthroat"
  ],
  "Guild Artisan / Sarevok, Deathbringer": [
    "Guild Artisan",
    "Sarevok, Deathbringer"
  ],
  "Guild Artisan / Shadowheart, Dark Justiciar": [
    "Guild Artisan",
    "Shadowheart, Dark Justiciar"
  ],
  "Guild Artisan / Sivriss, Nightmare Speaker": [
    "Guild Artisan",
    "Sivriss, Nightmare Speaker"
  ],
  "Guild Artisan / Skanos Dragonheart": [
    "Guild Artisan",
    "Skanos Dragonheart"
  ],
  "Guild Artisan / Vhal, Candlekeep Researcher": [
    "Guild Artisan",
    "Vhal, Candlekeep Researcher"
  ],
  "Guild Artisan / Viconia, Drow Apostate": [
    "Guild Artisan",
    "Viconia, Drow Apostate"
  ],
  "Guild Artisan / Volo, Itinerant Scholar": [
    "Guild Artisan",
    "Volo, Itinerant Scholar"
  ],
  "Guild Artisan / Wilson, Refined Grizzly": [
    "Guild Artisan",
    "Wilson, Refined Grizzly"
  ],
  "Guild Artisan / Wyll, Blade of Frontiers": [
    "Guild Artisan",
    "Wyll, Blade of Frontiers"
  ],
  "Guild Artisan / Zellix, Sanity Flayer": [
    "Guild Artisan",
    "Zellix, Sanity Flayer"
  ],
  "Gut, True Soul Zealot / Hardy Outlander": [
    "Gut, True Soul Zealot",
    "Hardy Outlander"
  ],
  "Gut, True Soul Zealot / Haunted One": [
    "Gut, True Soul Zealot",
    "Haunted One"
  ],
  "Gut, True Soul Zealot / Inspiring Leader": [
    "Gut, True Soul Zealot",
    "Inspiring Leader"
  ],
  "Gut, True Soul Zealot / Master Chef": [
    "Gut, True Soul Zealot",
    "Master Chef"
  ],
  "Gut, True Soul Zealot / Noble Heritage": [
    "Gut, True Soul Zealot",
    "Noble Heritage"
  ],
  "Gut, True Soul Zealot / Passionate Archaeologist": [
    "Gut, True Soul Zealot",
    "Passionate Archaeologist"
  ],
  "Gut, True Soul Zealot / Popular Entertainer": [
    "Gut, True Soul Zealot",
    "Popular Entertainer"
  ],
  "Gut, True Soul Zealot / Raised by Giants": [
    "Gut, True Soul Zealot",
    "Raised by Giants"
  ],
  "Gut, True Soul Zealot / Scion of Halaster": [
    "Gut, True Soul Zealot",
    "Scion of Halaster"
  ],
  "Gut, True Soul Zealot / Shameless Charlatan": [
    "Gut, True Soul Zealot",
    "Shameless Charlatan"
  ],
  "Gut, True Soul Zealot / Street Urchin": [
    "Gut, True Soul Zealot",
    "Street Urchin"
  ],
  "Gut, True Soul Zealot / Sword Coast Sailor": [
    "Gut, True Soul Zealot",
    "Sword Coast Sailor"
  ],
  "Gut, True Soul Zealot / Tavern Brawler": [
    "Gut, True Soul Zealot",
    "Tavern Brawler"
  ],
  "Gut, True Soul Zealot / Veteran Soldier": [
    "Gut, True Soul Zealot",
    "Veteran Soldier"
  ],
  "Halana, Kessig Ranger / Ich-Tekik, Salvage Splicer": [
    "Halana, Kessig Ranger",
    "Ich-Tekik, Salvage Splicer"
  ],
  "Halana, Kessig Ranger / Ikra Shidiqi, the Usurper": [
    "Halana, Kessig Ranger",
    "Ikra Shidiqi, the Usurper"
  ],
  "Halana, Kessig Ranger / Ishai, Ojutai Dragonspeaker": [
    "Halana, Kessig Ranger",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Halana, Kessig Ranger / Jeska, Thrice Reborn": [
    "Halana, Kessig Ranger",
    "Jeska, Thrice Reborn"
  ],
  "Halana, Kessig Ranger / Kamahl, Heart of Krosa": [
    "Halana, Kessig Ranger",
    "Kamahl, Heart of Krosa"
  ],
  "Halana, Kessig Ranger / Kediss, Emberclaw Familiar": [
    "Halana, Kessig Ranger",
    "Kediss, Emberclaw Familiar"
  ],
  "Halana, Kessig Ranger / Keleth, Sunmane Familiar": [
    "Halana, Kessig Ranger",
    "Keleth, Sunmane Familiar"
  ],
  "Halana, Kessig Ranger / Keskit, the Flesh Sculptor": [
    "Halana, Kessig Ranger",
    "Keskit, the Flesh Sculptor"
  ],
  "Halana, Kessig Ranger / Kodama of the East Tree": [
    "Halana, Kessig Ranger",
    "Kodama of the East Tree"
  ],
  "Halana, Kessig Ranger / Krark, the Thumbless": [
    "Halana, Kessig Ranger",
    "Krark, the Thumbless"
  ],
  "Halana, Kessig Ranger / Kraum, Ludevic's Opus": [
    "Halana, Kessig Ranger",
    "Kraum, Ludevic's Opus"
  ],
  "Halana, Kessig Ranger / Kydele, Chosen of Kruphix": [
    "Halana, Kessig Ranger",
    "Kydele, Chosen of Kruphix"
  ],
  "Halana, Kessig Ranger / Livio, Oathsworn Sentinel": [
    "Halana, Kessig Ranger",
    "Livio, Oathsworn Sentinel"
  ],
  "Halana, Kessig Ranger / Ludevic, Necro-Alchemist": [
    "Halana, Kessig Ranger",
    "Ludevic, Necro-Alchemist"
  ],
  "Halana, Kessig Ranger / Malcolm, Keen-Eyed Navigator": [
    "Halana, Kessig Ranger",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Halana, Kessig Ranger / Miara, Thorn of the Glade": [
    "Halana, Kessig Ranger",
    "Miara, Thorn of the Glade"
  ],
  "Halana, Kessig Ranger / Nadier, Agent of the Duskenel": [
    "Halana, Kessig Ranger",
    "Nadier, Agent of the Duskenel"
  ],
  "Halana, Kessig Ranger / Numa, Joraga Chieftain": [
    "Halana, Kessig Ranger",
    "Numa, Joraga Chieftain"
  ],
  "Halana, Kessig Ranger / Prava of the Steel Legion": [
    "Halana, Kessig Ranger",
    "Prava of the Steel Legion"
  ],
  "Halana, Kessig Ranger / Radiant, Serra Archangel": [
    "Halana, Kessig Ranger",
    "Radiant, Serra Archangel"
  ],
  "Halana, Kessig Ranger / Ravos, Soultender": [
    "Halana, Kessig Ranger",
    "Ravos, Soultender"
  ],
  "Halana, Kessig Ranger / Rebbec, Architect of Ascension": [
    "Halana, Kessig Ranger",
    "Rebbec, Architect of Ascension"
  ],
  "Halana, Kessig Ranger / Reyhan, Last of the Abzan": [
    "Halana, Kessig Ranger",
    "Reyhan, Last of the Abzan"
  ],
  "Halana, Kessig Ranger / Rograkh, Son of Rohgahh": [
    "Halana, Kessig Ranger",
    "Rograkh, Son of Rohgahh"
  ],
  "Halana, Kessig Ranger / Sakashima of a Thousand Faces": [
    "Halana, Kessig Ranger",
    "Sakashima of a Thousand Faces"
  ],
  "Halana, Kessig Ranger / Sengir, the Dark Baron": [
    "Halana, Kessig Ranger",
    "Sengir, the Dark Baron"
  ],
  "Halana, Kessig Ranger / Siani, Eye of the Storm": [
    "Halana, Kessig Ranger",
    "Siani, Eye of the Storm"
  ],
  "Halana, Kessig Ranger / Sidar Kondo of Jamuraa": [
    "Halana, Kessig Ranger",
    "Sidar Kondo of Jamuraa"
  ],
  "Halana, Kessig Ranger / Silas Renn, Seeker Adept": [
    "Halana, Kessig Ranger",
    "Silas Renn, Seeker Adept"
  ],
  "Halana, Kessig Ranger / Slurrk, All-Ingesting": [
    "Halana, Kessig Ranger",
    "Slurrk, All-Ingesting"
  ],
  "Halana, Kessig Ranger / Tana, the Bloodsower": [
    "Halana, Kessig Ranger",
    "Tana, the Bloodsower"
  ],
  "Halana, Kessig Ranger / Tevesh Szat, Doom of Fools": [
    "Halana, Kessig Ranger",
    "Tevesh Szat, Doom of Fools"
  ],
  "Halana, Kessig Ranger / The Prismatic Piper": [
    "Halana, Kessig Ranger",
    "The Prismatic Piper"
  ],
  "Halana, Kessig Ranger / Thrasios, Triton Hero": [
    "Halana, Kessig Ranger",
    "Thrasios, Triton Hero"
  ],
  "Halana, Kessig Ranger / Toggo, Goblin Weaponsmith": [
    "Halana, Kessig Ranger",
    "Toggo, Goblin Weaponsmith"
  ],
  "Halana, Kessig Ranger / Tormod, the Desecrator": [
    "Halana, Kessig Ranger",
    "Tormod, the Desecrator"
  ],
  "Halana, Kessig Ranger / Tymna the Weaver": [
    "Halana, Kessig Ranger",
    "Tymna the Weaver"
  ],
  "Halana, Kessig Ranger / Vial Smasher the Fierce": [
    "Halana, Kessig Ranger",
    "Vial Smasher the Fierce"
  ],
  "Halana, Kessig Ranger / Yoshimaru, Ever Faithful": [
    "Halana, Kessig Ranger",
    "Yoshimaru, Ever Faithful"
  ],
  "Haldan, Avid Arcanist / Pako, Arcane Retriever": [
    "Pako, Arcane Retriever",
    "Haldan, Avid Arcanist"
  ],
  "Halsin, Emerald Archdruid / Hardy Outlander": [
    "Halsin, Emerald Archdruid",
    "Hardy Outlander"
  ],
  "Halsin, Emerald Archdruid / Haunted One": [
    "Halsin, Emerald Archdruid",
    "Haunted One"
  ],
  "Halsin, Emerald Archdruid / Inspiring Leader": [
    "Halsin, Emerald Archdruid",
    "Inspiring Leader"
  ],
  "Halsin, Emerald Archdruid / Master Chef": [
    "Halsin, Emerald Archdruid",
    "Master Chef"
  ],
  "Halsin, Emerald Archdruid / Noble Heritage": [
    "Halsin, Emerald Archdruid",
    "Noble Heritage"
  ],
  "Halsin, Emerald Archdruid / Passionate Archaeologist": [
    "Halsin, Emerald Archdruid",
    "Passionate Archaeologist"
  ],
  "Halsin, Emerald Archdruid / Popular Entertainer": [
    "Halsin, Emerald Archdruid",
    "Popular Entertainer"
  ],
  "Halsin, Emerald Archdruid / Raised by Giants": [
    "Halsin, Emerald Archdruid",
    "Raised by Giants"
  ],
  "Halsin, Emerald Archdruid / Scion of Halaster": [
    "Halsin, Emerald Archdruid",
    "Scion of Halaster"
  ],
  "Halsin, Emerald Archdruid / Shameless Charlatan": [
    "Halsin, Emerald Archdruid",
    "Shameless Charlatan"
  ],
  "Halsin, Emerald Archdruid / Street Urchin": [
    "Halsin, Emerald Archdruid",
    "Street Urchin"
  ],
  "Halsin, Emerald Archdruid / Sword Coast Sailor": [
    "Halsin, Emerald Archdruid",
    "Sword Coast Sailor"
  ],
  "Halsin, Emerald Archdruid / Tavern Brawler": [
    "Halsin, Emerald Archdruid",
    "Tavern Brawler"
  ],
  "Halsin, Emerald Archdruid / Veteran Soldier": [
    "Halsin, Emerald Archdruid",
    "Veteran Soldier"
  ],
  "Hardy Outlander / Imoen, Mystic Trickster": [
    "Hardy Outlander",
    "Imoen, Mystic Trickster"
  ],
  "Hardy Outlander / Jaheira, Friend of the Forest": [
    "Hardy Outlander",
    "Jaheira, Friend of the Forest"
  ],
  "Hardy Outlander / Karlach, Fury of Avernus": [
    "Hardy Outlander",
    "Karlach, Fury of Avernus"
  ],
  "Hardy Outlander / Lae'zel, Vlaakith's Champion": [
    "Hardy Outlander",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Hardy Outlander / Livaan, Cultist of Tiamat": [
    "Hardy Outlander",
    "Livaan, Cultist of Tiamat"
  ],
  "Hardy Outlander / Lulu, Loyal Hollyphant": [
    "Hardy Outlander",
    "Lulu, Loyal Hollyphant"
  ],
  "Hardy Outlander / Rasaad yn Bashir": [
    "Hardy Outlander",
    "Rasaad yn Bashir"
  ],
  "Hardy Outlander / Renari, Merchant of Marvels": [
    "Hardy Outlander",
    "Renari, Merchant of Marvels"
  ],
  "Hardy Outlander / Safana, Calimport Cutthroat": [
    "Hardy Outlander",
    "Safana, Calimport Cutthroat"
  ],
  "Hardy Outlander / Sarevok, Deathbringer": [
    "Hardy Outlander",
    "Sarevok, Deathbringer"
  ],
  "Hardy Outlander / Shadowheart, Dark Justiciar": [
    "Hardy Outlander",
    "Shadowheart, Dark Justiciar"
  ],
  "Hardy Outlander / Sivriss, Nightmare Speaker": [
    "Hardy Outlander",
    "Sivriss, Nightmare Speaker"
  ],
  "Hardy Outlander / Skanos Dragonheart": [
    "Hardy Outlander",
    "Skanos Dragonheart"
  ],
  "Hardy Outlander / Vhal, Candlekeep Researcher": [
    "Hardy Outlander",
    "Vhal, Candlekeep Researcher"
  ],
  "Hardy Outlander / Viconia, Drow Apostate": [
    "Hardy Outlander",
    "Viconia, Drow Apostate"
  ],
  "Hardy Outlander / Volo, Itinerant Scholar": [
    "Hardy Outlander",
    "Volo, Itinerant Scholar"
  ],
  "Hardy Outlander / Wilson, Refined Grizzly": [
    "Hardy Outlander",
    "Wilson, Refined Grizzly"
  ],
  "Hardy Outlander / Wyll, Blade of Frontiers": [
    "Hardy Outlander",
    "Wyll, Blade of Frontiers"
  ],
  "Hardy Outlander / Zellix, Sanity Flayer": [
    "Hardy Outlander",
    "Zellix, Sanity Flayer"
  ],
  "Hargilde, Kindly Runechanter / Othelm, Sigardian Outcast": [
    "Hargilde, Kindly Runechanter",
    "Othelm, Sigardian Outcast"
  ],
  "Hargilde, Kindly Runechanter / Sophina, Spearsage Deserter": [
    "Hargilde, Kindly Runechanter",
    "Sophina, Spearsage Deserter"
  ],
  "Hargilde, Kindly Runechanter / Wernog, Rider's Chaplain": [
    "Hargilde, Kindly Runechanter",
    "Wernog, Rider's Chaplain"
  ],
  "Haunted One / Imoen, Mystic Trickster": [
    "Haunted One",
    "Imoen, Mystic Trickster"
  ],
  "Haunted One / Jaheira, Friend of the Forest": [
    "Haunted One",
    "Jaheira, Friend of the Forest"
  ],
  "Haunted One / Karlach, Fury of Avernus": [
    "Haunted One",
    "Karlach, Fury of Avernus"
  ],
  "Haunted One / Lae'zel, Vlaakith's Champion": [
    "Haunted One",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Haunted One / Livaan, Cultist of Tiamat": [
    "Haunted One",
    "Livaan, Cultist of Tiamat"
  ],
  "Haunted One / Lulu, Loyal Hollyphant": [
    "Haunted One",
    "Lulu, Loyal Hollyphant"
  ],
  "Haunted One / Rasaad yn Bashir": [
    "Haunted One",
    "Rasaad yn Bashir"
  ],
  "Haunted One / Renari, Merchant of Marvels": [
    "Haunted One",
    "Renari, Merchant of Marvels"
  ],
  "Haunted One / Safana, Calimport Cutthroat": [
    "Haunted One",
    "Safana, Calimport Cutthroat"
  ],
  "Haunted One / Sarevok, Deathbringer": [
    "Haunted One",
    "Sarevok, Deathbringer"
  ],
  "Haunted One / Shadowheart, Dark Justiciar": [
    "Haunted One",
    "Shadowheart, Dark Justiciar"
  ],
  "Haunted One / Sivriss, Nightmare Speaker": [
    "Haunted One",
    "Sivriss, Nightmare Speaker"
  ],
  "Haunted One / Skanos Dragonheart": [
    "Haunted One",
    "Skanos Dragonheart"
  ],
  "Haunted One / Vhal, Candlekeep Researcher": [
    "Haunted One",
    "Vhal, Candlekeep Researcher"
  ],
  "Haunted One / Viconia, Drow Apostate": [
    "Haunted One",
    "Viconia, Drow Apostate"
  ],
  "Haunted One / Volo, Itinerant Scholar": [
    "Haunted One",
    "Volo, Itinerant Scholar"
  ],
  "Haunted One / Wilson, Refined Grizzly": [
    "Haunted One",
    "Wilson, Refined Grizzly"
  ],
  "Haunted One / Wyll, Blade of Frontiers": [
    "Haunted One",
    "Wyll, Blade of Frontiers"
  ],
  "Haunted One / Zellix, Sanity Flayer": [
    "Haunted One",
    "Zellix, Sanity Flayer"
  ],
  "Ian Chesterton / The Eighth Doctor": [
    "Ian Chesterton",
    "The Eighth Doctor"
  ],
  "Ian Chesterton / The Eleventh Doctor": [
    "Ian Chesterton",
    "The Eleventh Doctor"
  ],
  "Ian Chesterton / The Fifteenth Doctor": [
    "Ian Chesterton",
    "The Fifteenth Doctor"
  ],
  "Ian Chesterton / The Fifth Doctor": [
    "Ian Chesterton",
    "The Fifth Doctor"
  ],
  "Ian Chesterton / The First Doctor": [
    "Ian Chesterton",
    "The First Doctor"
  ],
  "Ian Chesterton / The Fourteenth Doctor": [
    "Ian Chesterton",
    "The Fourteenth Doctor"
  ],
  "Ian Chesterton / The Fourth Doctor": [
    "Ian Chesterton",
    "The Fourth Doctor"
  ],
  "Ian Chesterton / The Fugitive Doctor": [
    "Ian Chesterton",
    "The Fugitive Doctor"
  ],
  "Ian Chesterton / The Ninth Doctor": [
    "Ian Chesterton",
    "The Ninth Doctor"
  ],
  "Ian Chesterton / The Second Doctor": [
    "Ian Chesterton",
    "The Second Doctor"
  ],
  "Ian Chesterton / The Seventh Doctor": [
    "Ian Chesterton",
    "The Seventh Doctor"
  ],
  "Ian Chesterton / The Sixth Doctor": [
    "Ian Chesterton",
    "The Sixth Doctor"
  ],
  "Ian Chesterton / The Tenth Doctor": [
    "Ian Chesterton",
    "The Tenth Doctor"
  ],
  "Ian Chesterton / The Third Doctor": [
    "Ian Chesterton",
    "The Third Doctor"
  ],
  "Ian Chesterton / The Thirteenth Doctor": [
    "Ian Chesterton",
    "The Thirteenth Doctor"
  ],
  "Ian Chesterton / The Twelfth Doctor": [
    "Ian Chesterton",
    "The Twelfth Doctor"
  ],
  "Ian Chesterton / The War Doctor": [
    "Ian Chesterton",
    "The War Doctor"
  ],
  "Ich-Tekik, Salvage Splicer / Ikra Shidiqi, the Usurper": [
    "Ich-Tekik, Salvage Splicer",
    "Ikra Shidiqi, the Usurper"
  ],
  "Ich-Tekik, Salvage Splicer / Ishai, Ojutai Dragonspeaker": [
    "Ich-Tekik, Salvage Splicer",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ich-Tekik, Salvage Splicer / Jeska, Thrice Reborn": [
    "Ich-Tekik, Salvage Splicer",
    "Jeska, Thrice Reborn"
  ],
  "Ich-Tekik, Salvage Splicer / Kamahl, Heart of Krosa": [
    "Ich-Tekik, Salvage Splicer",
    "Kamahl, Heart of Krosa"
  ],
  "Ich-Tekik, Salvage Splicer / Kediss, Emberclaw Familiar": [
    "Ich-Tekik, Salvage Splicer",
    "Kediss, Emberclaw Familiar"
  ],
  "Ich-Tekik, Salvage Splicer / Keleth, Sunmane Familiar": [
    "Ich-Tekik, Salvage Splicer",
    "Keleth, Sunmane Familiar"
  ],
  "Ich-Tekik, Salvage Splicer / Keskit, the Flesh Sculptor": [
    "Ich-Tekik, Salvage Splicer",
    "Keskit, the Flesh Sculptor"
  ],
  "Ich-Tekik, Salvage Splicer / Kodama of the East Tree": [
    "Ich-Tekik, Salvage Splicer",
    "Kodama of the East Tree"
  ],
  "Ich-Tekik, Salvage Splicer / Krark, the Thumbless": [
    "Ich-Tekik, Salvage Splicer",
    "Krark, the Thumbless"
  ],
  "Ich-Tekik, Salvage Splicer / Kraum, Ludevic's Opus": [
    "Ich-Tekik, Salvage Splicer",
    "Kraum, Ludevic's Opus"
  ],
  "Ich-Tekik, Salvage Splicer / Kydele, Chosen of Kruphix": [
    "Ich-Tekik, Salvage Splicer",
    "Kydele, Chosen of Kruphix"
  ],
  "Ich-Tekik, Salvage Splicer / Livio, Oathsworn Sentinel": [
    "Ich-Tekik, Salvage Splicer",
    "Livio, Oathsworn Sentinel"
  ],
  "Ich-Tekik, Salvage Splicer / Ludevic, Necro-Alchemist": [
    "Ich-Tekik, Salvage Splicer",
    "Ludevic, Necro-Alchemist"
  ],
  "Ich-Tekik, Salvage Splicer / Malcolm, Keen-Eyed Navigator": [
    "Ich-Tekik, Salvage Splicer",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ich-Tekik, Salvage Splicer / Miara, Thorn of the Glade": [
    "Ich-Tekik, Salvage Splicer",
    "Miara, Thorn of the Glade"
  ],
  "Ich-Tekik, Salvage Splicer / Nadier, Agent of the Duskenel": [
    "Ich-Tekik, Salvage Splicer",
    "Nadier, Agent of the Duskenel"
  ],
  "Ich-Tekik, Salvage Splicer / Numa, Joraga Chieftain": [
    "Ich-Tekik, Salvage Splicer",
    "Numa, Joraga Chieftain"
  ],
  "Ich-Tekik, Salvage Splicer / Prava of the Steel Legion": [
    "Ich-Tekik, Salvage Splicer",
    "Prava of the Steel Legion"
  ],
  "Ich-Tekik, Salvage Splicer / Radiant, Serra Archangel": [
    "Ich-Tekik, Salvage Splicer",
    "Radiant, Serra Archangel"
  ],
  "Ich-Tekik, Salvage Splicer / Ravos, Soultender": [
    "Ich-Tekik, Salvage Splicer",
    "Ravos, Soultender"
  ],
  "Ich-Tekik, Salvage Splicer / Rebbec, Architect of Ascension": [
    "Ich-Tekik, Salvage Splicer",
    "Rebbec, Architect of Ascension"
  ],
  "Ich-Tekik, Salvage Splicer / Reyhan, Last of the Abzan": [
    "Ich-Tekik, Salvage Splicer",
    "Reyhan, Last of the Abzan"
  ],
  "Ich-Tekik, Salvage Splicer / Rograkh, Son of Rohgahh": [
    "Ich-Tekik, Salvage Splicer",
    "Rograkh, Son of Rohgahh"
  ],
  "Ich-Tekik, Salvage Splicer / Sakashima of a Thousand Faces": [
    "Ich-Tekik, Salvage Splicer",
    "Sakashima of a Thousand Faces"
  ],
  "Ich-Tekik, Salvage Splicer / Sengir, the Dark Baron": [
    "Ich-Tekik, Salvage Splicer",
    "Sengir, the Dark Baron"
  ],
  "Ich-Tekik, Salvage Splicer / Siani, Eye of the Storm": [
    "Ich-Tekik, Salvage Splicer",
    "Siani, Eye of the Storm"
  ],
  "Ich-Tekik, Salvage Splicer / Sidar Kondo of Jamuraa": [
    "Ich-Tekik, Salvage Splicer",
    "Sidar Kondo of Jamuraa"
  ],
  "Ich-Tekik, Salvage Splicer / Silas Renn, Seeker Adept": [
    "Ich-Tekik, Salvage Splicer",
    "Silas Renn, Seeker Adept"
  ],
  "Ich-Tekik, Salvage Splicer / Slurrk, All-Ingesting": [
    "Ich-Tekik, Salvage Splicer",
    "Slurrk, All-Ingesting"
  ],
  "Ich-Tekik, Salvage Splicer / Tana, the Bloodsower": [
    "Ich-Tekik, Salvage Splicer",
    "Tana, the Bloodsower"
  ],
  "Ich-Tekik, Salvage Splicer / Tevesh Szat, Doom of Fools": [
    "Ich-Tekik, Salvage Splicer",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ich-Tekik, Salvage Splicer / The Prismatic Piper": [
    "Ich-Tekik, Salvage Splicer",
    "The Prismatic Piper"
  ],
  "Ich-Tekik, Salvage Splicer / Thrasios, Triton Hero": [
    "Ich-Tekik, Salvage Splicer",
    "Thrasios, Triton Hero"
  ],
  "Ich-Tekik, Salvage Splicer / Toggo, Goblin Weaponsmith": [
    "Ich-Tekik, Salvage Splicer",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ich-Tekik, Salvage Splicer / Tormod, the Desecrator": [
    "Ich-Tekik, Salvage Splicer",
    "Tormod, the Desecrator"
  ],
  "Ich-Tekik, Salvage Splicer / Tymna the Weaver": [
    "Ich-Tekik, Salvage Splicer",
    "Tymna the Weaver"
  ],
  "Ich-Tekik, Salvage Splicer / Vial Smasher the Fierce": [
    "Ich-Tekik, Salvage Splicer",
    "Vial Smasher the Fierce"
  ],
  "Ich-Tekik, Salvage Splicer / Yoshimaru, Ever Faithful": [
    "Ich-Tekik, Salvage Splicer",
    "Yoshimaru, Ever Faithful"
  ],
  "Ikra Shidiqi, the Usurper / Ishai, Ojutai Dragonspeaker": [
    "Ikra Shidiqi, the Usurper",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ikra Shidiqi, the Usurper / Jeska, Thrice Reborn": [
    "Ikra Shidiqi, the Usurper",
    "Jeska, Thrice Reborn"
  ],
  "Ikra Shidiqi, the Usurper / Kamahl, Heart of Krosa": [
    "Ikra Shidiqi, the Usurper",
    "Kamahl, Heart of Krosa"
  ],
  "Ikra Shidiqi, the Usurper / Kediss, Emberclaw Familiar": [
    "Ikra Shidiqi, the Usurper",
    "Kediss, Emberclaw Familiar"
  ],
  "Ikra Shidiqi, the Usurper / Keleth, Sunmane Familiar": [
    "Ikra Shidiqi, the Usurper",
    "Keleth, Sunmane Familiar"
  ],
  "Ikra Shidiqi, the Usurper / Keskit, the Flesh Sculptor": [
    "Ikra Shidiqi, the Usurper",
    "Keskit, the Flesh Sculptor"
  ],
  "Ikra Shidiqi, the Usurper / Kodama of the East Tree": [
    "Ikra Shidiqi, the Usurper",
    "Kodama of the East Tree"
  ],
  "Ikra Shidiqi, the Usurper / Krark, the Thumbless": [
    "Ikra Shidiqi, the Usurper",
    "Krark, the Thumbless"
  ],
  "Ikra Shidiqi, the Usurper / Kraum, Ludevic's Opus": [
    "Ikra Shidiqi, the Usurper",
    "Kraum, Ludevic's Opus"
  ],
  "Ikra Shidiqi, the Usurper / Kydele, Chosen of Kruphix": [
    "Ikra Shidiqi, the Usurper",
    "Kydele, Chosen of Kruphix"
  ],
  "Ikra Shidiqi, the Usurper / Livio, Oathsworn Sentinel": [
    "Ikra Shidiqi, the Usurper",
    "Livio, Oathsworn Sentinel"
  ],
  "Ikra Shidiqi, the Usurper / Ludevic, Necro-Alchemist": [
    "Ikra Shidiqi, the Usurper",
    "Ludevic, Necro-Alchemist"
  ],
  "Ikra Shidiqi, the Usurper / Malcolm, Keen-Eyed Navigator": [
    "Ikra Shidiqi, the Usurper",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ikra Shidiqi, the Usurper / Miara, Thorn of the Glade": [
    "Ikra Shidiqi, the Usurper",
    "Miara, Thorn of the Glade"
  ],
  "Ikra Shidiqi, the Usurper / Nadier, Agent of the Duskenel": [
    "Ikra Shidiqi, the Usurper",
    "Nadier, Agent of the Duskenel"
  ],
  "Ikra Shidiqi, the Usurper / Numa, Joraga Chieftain": [
    "Ikra Shidiqi, the Usurper",
    "Numa, Joraga Chieftain"
  ],
  "Ikra Shidiqi, the Usurper / Prava of the Steel Legion": [
    "Ikra Shidiqi, the Usurper",
    "Prava of the Steel Legion"
  ],
  "Ikra Shidiqi, the Usurper / Radiant, Serra Archangel": [
    "Ikra Shidiqi, the Usurper",
    "Radiant, Serra Archangel"
  ],
  "Ikra Shidiqi, the Usurper / Ravos, Soultender": [
    "Ikra Shidiqi, the Usurper",
    "Ravos, Soultender"
  ],
  "Ikra Shidiqi, the Usurper / Rebbec, Architect of Ascension": [
    "Ikra Shidiqi, the Usurper",
    "Rebbec, Architect of Ascension"
  ],
  "Ikra Shidiqi, the Usurper / Reyhan, Last of the Abzan": [
    "Ikra Shidiqi, the Usurper",
    "Reyhan, Last of the Abzan"
  ],
  "Ikra Shidiqi, the Usurper / Rograkh, Son of Rohgahh": [
    "Ikra Shidiqi, the Usurper",
    "Rograkh, Son of Rohgahh"
  ],
  "Ikra Shidiqi, the Usurper / Sakashima of a Thousand Faces": [
    "Ikra Shidiqi, the Usurper",
    "Sakashima of a Thousand Faces"
  ],
  "Ikra Shidiqi, the Usurper / Sengir, the Dark Baron": [
    "Ikra Shidiqi, the Usurper",
    "Sengir, the Dark Baron"
  ],
  "Ikra Shidiqi, the Usurper / Siani, Eye of the Storm": [
    "Ikra Shidiqi, the Usurper",
    "Siani, Eye of the Storm"
  ],
  "Ikra Shidiqi, the Usurper / Sidar Kondo of Jamuraa": [
    "Ikra Shidiqi, the Usurper",
    "Sidar Kondo of Jamuraa"
  ],
  "Ikra Shidiqi, the Usurper / Silas Renn, Seeker Adept": [
    "Ikra Shidiqi, the Usurper",
    "Silas Renn, Seeker Adept"
  ],
  "Ikra Shidiqi, the Usurper / Slurrk, All-Ingesting": [
    "Ikra Shidiqi, the Usurper",
    "Slurrk, All-Ingesting"
  ],
  "Ikra Shidiqi, the Usurper / Tana, the Bloodsower": [
    "Ikra Shidiqi, the Usurper",
    "Tana, the Bloodsower"
  ],
  "Ikra Shidiqi, the Usurper / Tevesh Szat, Doom of Fools": [
    "Ikra Shidiqi, the Usurper",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ikra Shidiqi, the Usurper / The Prismatic Piper": [
    "Ikra Shidiqi, the Usurper",
    "The Prismatic Piper"
  ],
  "Ikra Shidiqi, the Usurper / Thrasios, Triton Hero": [
    "Ikra Shidiqi, the Usurper",
    "Thrasios, Triton Hero"
  ],
  "Ikra Shidiqi, the Usurper / Toggo, Goblin Weaponsmith": [
    "Ikra Shidiqi, the Usurper",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ikra Shidiqi, the Usurper / Tormod, the Desecrator": [
    "Ikra Shidiqi, the Usurper",
    "Tormod, the Desecrator"
  ],
  "Ikra Shidiqi, the Usurper / Tymna the Weaver": [
    "Ikra Shidiqi, the Usurper",
    "Tymna the Weaver"
  ],
  "Ikra Shidiqi, the Usurper / Vial Smasher the Fierce": [
    "Ikra Shidiqi, the Usurper",
    "Vial Smasher the Fierce"
  ],
  "Ikra Shidiqi, the Usurper / Yoshimaru, Ever Faithful": [
    "Ikra Shidiqi, the Usurper",
    "Yoshimaru, Ever Faithful"
  ],
  "Imoen, Mystic Trickster / Inspiring Leader": [
    "Imoen, Mystic Trickster",
    "Inspiring Leader"
  ],
  "Imoen, Mystic Trickster / Master Chef": [
    "Imoen, Mystic Trickster",
    "Master Chef"
  ],
  "Imoen, Mystic Trickster / Noble Heritage": [
    "Imoen, Mystic Trickster",
    "Noble Heritage"
  ],
  "Imoen, Mystic Trickster / Passionate Archaeologist": [
    "Imoen, Mystic Trickster",
    "Passionate Archaeologist"
  ],
  "Imoen, Mystic Trickster / Popular Entertainer": [
    "Imoen, Mystic Trickster",
    "Popular Entertainer"
  ],
  "Imoen, Mystic Trickster / Raised by Giants": [
    "Imoen, Mystic Trickster",
    "Raised by Giants"
  ],
  "Imoen, Mystic Trickster / Scion of Halaster": [
    "Imoen, Mystic Trickster",
    "Scion of Halaster"
  ],
  "Imoen, Mystic Trickster / Shameless Charlatan": [
    "Imoen, Mystic Trickster",
    "Shameless Charlatan"
  ],
  "Imoen, Mystic Trickster / Street Urchin": [
    "Imoen, Mystic Trickster",
    "Street Urchin"
  ],
  "Imoen, Mystic Trickster / Sword Coast Sailor": [
    "Imoen, Mystic Trickster",
    "Sword Coast Sailor"
  ],
  "Imoen, Mystic Trickster / Tavern Brawler": [
    "Imoen, Mystic Trickster",
    "Tavern Brawler"
  ],
  "Imoen, Mystic Trickster / Veteran Soldier": [
    "Imoen, Mystic Trickster",
    "Veteran Soldier"
  ],
  "Inspiring Leader / Jaheira, Friend of the Forest": [
    "Inspiring Leader",
    "Jaheira, Friend of the Forest"
  ],
  "Inspiring Leader / Karlach, Fury of Avernus": [
    "Inspiring Leader",
    "Karlach, Fury of Avernus"
  ],
  "Inspiring Leader / Lae'zel, Vlaakith's Champion": [
    "Inspiring Leader",
    "Lae'zel, Vlaakith's Champion"
  ],
  "Inspiring Leader / Livaan, Cultist of Tiamat": [
    "Inspiring Leader",
    "Livaan, Cultist of Tiamat"
  ],
  "Inspiring Leader / Lulu, Loyal Hollyphant": [
    "Inspiring Leader",
    "Lulu, Loyal Hollyphant"
  ],
  "Inspiring Leader / Rasaad yn Bashir": [
    "Inspiring Leader",
    "Rasaad yn Bashir"
  ],
  "Inspiring Leader / Renari, Merchant of Marvels": [
    "Inspiring Leader",
    "Renari, Merchant of Marvels"
  ],
  "Inspiring Leader / Safana, Calimport Cutthroat": [
    "Inspiring Leader",
    "Safana, Calimport Cutthroat"
  ],
  "Inspiring Leader / Sarevok, Deathbringer": [
    "Inspiring Leader",
    "Sarevok, Deathbringer"
  ],
  "Inspiring Leader / Shadowheart, Dark Justiciar": [
    "Inspiring Leader",
    "Shadowheart, Dark Justiciar"
  ],
  "Inspiring Leader / Sivriss, Nightmare Speaker": [
    "Inspiring Leader",
    "Sivriss, Nightmare Speaker"
  ],
  "Inspiring Leader / Skanos Dragonheart": [
    "Inspiring Leader",
    "Skanos Dragonheart"
  ],
  "Inspiring Leader / Vhal, Candlekeep Researcher": [
    "Inspiring Leader",
    "Vhal, Candlekeep Researcher"
  ],
  "Inspiring Leader / Viconia, Drow Apostate": [
    "Inspiring Leader",
    "Viconia, Drow Apostate"
  ],
  "Inspiring Leader / Volo, Itinerant Scholar": [
    "Inspiring Leader",
    "Volo, Itinerant Scholar"
  ],
  "Inspiring Leader / Wilson, Refined Grizzly": [
    "Inspiring Leader",
    "Wilson, Refined Grizzly"
  ],
  "Inspiring Leader / Wyll, Blade of Frontiers": [
    "Inspiring Leader",
    "Wyll, Blade of Frontiers"
  ],
  "Inspiring Leader / Zellix, Sanity Flayer": [
    "Inspiring Leader",
    "Zellix, Sanity Flayer"
  ],
  "Ishai, Ojutai Dragonspeaker / Jeska, Thrice Reborn": [
    "Jeska, Thrice Reborn",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ishai, Ojutai Dragonspeaker / Kamahl, Heart of Krosa": [
    "Ishai, Ojutai Dragonspeaker",
    "Kamahl, Heart of Krosa"
  ],
  "Ishai, Ojutai Dragonspeaker / Kediss, Emberclaw Familiar": [
    "Ishai, Ojutai Dragonspeaker",
    "Kediss, Emberclaw Familiar"
  ],
  "Ishai, Ojutai Dragonspeaker / Keleth, Sunmane Familiar": [
    "Ishai, Ojutai Dragonspeaker",
    "Keleth, Sunmane Familiar"
  ],
  "Ishai, Ojutai Dragonspeaker / Keskit, the Flesh Sculptor": [
    "Ishai, Ojutai Dragonspeaker",
    "Keskit, the Flesh Sculptor"
  ],
  "Ishai, Ojutai Dragonspeaker / Kodama of the East Tree": [
    "Ishai, Ojutai Dragonspeaker",
    "Kodama of the East Tree"
  ],
  "Ishai, Ojutai Dragonspeaker / Krark, the Thumbless": [
    "Ishai, Ojutai Dragonspeaker",
    "Krark, the Thumbless"
  ],
  "Ishai, Ojutai Dragonspeaker / Kraum, Ludevic's Opus": [
    "Ishai, Ojutai Dragonspeaker",
    "Kraum, Ludevic's Opus"
  ],
  "Ishai, Ojutai Dragonspeaker / Kydele, Chosen of Kruphix": [
    "Ishai, Ojutai Dragonspeaker",
    "Kydele, Chosen of Kruphix"
  ],
  "Ishai, Ojutai Dragonspeaker / Livio, Oathsworn Sentinel": [
    "Ishai, Ojutai Dragonspeaker",
    "Livio, Oathsworn Sentinel"
  ],
  "Ishai, Ojutai Dragonspeaker / Ludevic, Necro-Alchemist": [
    "Ishai, Ojutai Dragonspeaker",
    "Ludevic, Necro-Alchemist"
  ],
  "Ishai, Ojutai Dragonspeaker / Malcolm, Keen-Eyed Navigator": [
    "Ishai, Ojutai Dragonspeaker",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ishai, Ojutai Dragonspeaker / Miara, Thorn of the Glade": [
    "Ishai, Ojutai Dragonspeaker",
    "Miara, Thorn of the Glade"
  ],
  "Ishai, Ojutai Dragonspeaker / Nadier, Agent of the Duskenel": [
    "Ishai, Ojutai Dragonspeaker",
    "Nadier, Agent of the Duskenel"
  ],
  "Ishai, Ojutai Dragonspeaker / Numa, Joraga Chieftain": [
    "Ishai, Ojutai Dragonspeaker",
    "Numa, Joraga Chieftain"
  ],
  "Ishai, Ojutai Dragonspeaker / Prava of the Steel Legion": [
    "Ishai, Ojutai Dragonspeaker",
    "Prava of the Steel Legion"
  ],
  "Ishai, Ojutai Dragonspeaker / Radiant, Serra Archangel": [
    "Ishai, Ojutai Dragonspeaker",
    "Radiant, Serra Archangel"
  ],
  "Ishai, Ojutai Dragonspeaker / Ravos, Soultender": [
    "Ishai, Ojutai Dragonspeaker",
    "Ravos, Soultender"
  ],
  "Ishai, Ojutai Dragonspeaker / Rebbec, Architect of Ascension": [
    "Ishai, Ojutai Dragonspeaker",
    "Rebbec, Architect of Ascension"
  ],
  "Ishai, Ojutai Dragonspeaker / Reyhan, Last of the Abzan": [
    "Ishai, Ojutai Dragonspeaker",
    "Reyhan, Last of the Abzan"
  ],
  "Ishai, Ojutai Dragonspeaker / Rograkh, Son of Rohgahh": [
    "Rograkh, Son of Rohgahh",
    "Ishai, Ojutai Dragonspeaker"
  ],
  "Ishai, Ojutai Dragonspeaker / Sakashima of a Thousand Faces": [
    "Ishai, Ojutai Dragonspeaker",
    "Sakashima of a Thousand Faces"
  ],
  "Ishai, Ojutai Dragonspeaker / Sengir, the Dark Baron": [
    "Ishai, Ojutai Dragonspeaker",
    "Sengir, the Dark Baron"
  ],
  "Ishai, Ojutai Dragonspeaker / Siani, Eye of the Storm": [
    "Ishai, Ojutai Dragonspeaker",
    "Siani, Eye of the Storm"
  ],
  "Ishai, Ojutai Dragonspeaker / Sidar Kondo of Jamuraa": [
    "Ishai, Ojutai Dragonspeaker",
    "Sidar Kondo of Jamuraa"
  ],
  "Ishai, Ojutai Dragonspeaker / Silas Renn, Seeker Adept": [
    "Ishai, Ojutai Dragonspeaker",
    "Silas Renn, Seeker Adept"
  ],
  "Ishai, Ojutai Dragonspeaker / Slurrk, All-Ingesting": [
    "Ishai, Ojutai Dragonspeaker",
    "Slurrk, All-Ingesting"
  ],
  "Ishai, Ojutai Dragonspeaker / Tana, the Bloodsower": [
    "Ishai, Ojutai Dragonspeaker",
    "Tana, the Bloodsower"
  ],
  "Ishai, Ojutai Dragonspeaker / Tevesh Szat, Doom of Fools": [
    "Ishai, Ojutai Dragonspeaker",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ishai, Ojutai Dragonspeaker / The Prismatic Piper": [
    "Ishai, Ojutai Dragonspeaker",
    "The Prismatic Piper"
  ],
  "Ishai, Ojutai Dragonspeaker / Thrasios, Triton Hero": [
    "Ishai, Ojutai Dragonspeaker",
    "Thrasios, Triton Hero"
  ],
  "Ishai, Ojutai Dragonspeaker / Toggo, Goblin Weaponsmith": [
    "Ishai, Ojutai Dragonspeaker",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ishai, Ojutai Dragonspeaker / Tormod, the Desecrator": [
    "Ishai, Ojutai Dragonspeaker",
    "Tormod, the Desecrator"
  ],
  "Ishai, Ojutai Dragonspeaker / Tymna the Weaver": [
    "Ishai, Ojutai Dragonspeaker",
    "Tymna the Weaver"
  ],
  "Ishai, Ojutai Dragonspeaker / Vial Smasher the Fierce": [
    "Ishai, Ojutai Dragonspeaker",
    "Vial Smasher the Fierce"
  ],
  "Ishai, Ojutai Dragonspeaker / Yoshimaru, Ever Faithful": [
    "Ishai, Ojutai Dragonspeaker",
    "Yoshimaru, Ever Faithful"
  ],
  "Jaheira, Friend of the Forest / Master Chef": [
    "Jaheira, Friend of the Forest",
    "Master Chef"
  ],
  "Jaheira, Friend of the Forest / Noble Heritage": [
    "Jaheira, Friend of the Forest",
    "Noble Heritage"
  ],
  "Jaheira, Friend of the Forest / Passionate Archaeologist": [
    "Jaheira, Friend of the Forest",
    "Passionate Archaeologist"
  ],
  "Jaheira, Friend of the Forest / Popular Entertainer": [
    "Jaheira, Friend of the Forest",
    "Popular Entertainer"
  ],
  "Jaheira, Friend of the Forest / Raised by Giants": [
    "Jaheira, Friend of the Forest",
    "Raised by Giants"
  ],
  "Jaheira, Friend of the Forest / Scion of Halaster": [
    "Jaheira, Friend of the Forest",
    "Scion of Halaster"
  ],
  "Jaheira, Friend of the Forest / Shameless Charlatan": [
    "Jaheira, Friend of the Forest",
    "Shameless Charlatan"
  ],
  "Jaheira, Friend of the Forest / Street Urchin": [
    "Jaheira, Friend of the Forest",
    "Street Urchin"
  ],
  "Jaheira, Friend of the Forest / Sword Coast Sailor": [
    "Jaheira, Friend of the Forest",
    "Sword Coast Sailor"
  ],
  "Jaheira, Friend of the Forest / Tavern Brawler": [
    "Jaheira, Friend of the Forest",
    "Tavern Brawler"
  ],
  "Jaheira, Friend of the Forest / Veteran Soldier": [
    "Jaheira, Friend of the Forest",
    "Veteran Soldier"
  ],
  "Jamie McCrimmon / The Eighth Doctor": [
    "Jamie McCrimmon",
    "The Eighth Doctor"
  ],
  "Jamie McCrimmon / The Eleventh Doctor": [
    "Jamie McCrimmon",
    "The Eleventh Doctor"
  ],
  "Jamie McCrimmon / The Fifteenth Doctor": [
    "Jamie McCrimmon",
    "The Fifteenth Doctor"
  ],
  "Jamie McCrimmon / The Fifth Doctor": [
    "Jamie McCrimmon",
    "The Fifth Doctor"
  ],
  "Jamie McCrimmon / The First Doctor": [
    "Jamie McCrimmon",
    "The First Doctor"
  ],
  "Jamie McCrimmon / The Fourteenth Doctor": [
    "Jamie McCrimmon",
    "The Fourteenth Doctor"
  ],
  "Jamie McCrimmon / The Fourth Doctor": [
    "Jamie McCrimmon",
    "The Fourth Doctor"
  ],
  "Jamie McCrimmon / The Fugitive Doctor": [
    "Jamie McCrimmon",
    "The Fugitive Doctor"
  ],
  "Jamie McCrimmon / The Ninth Doctor": [
    "Jamie McCrimmon",
    "The Ninth Doctor"
  ],
  "Jamie McCrimmon / The Second Doctor": [
    "Jamie McCrimmon",
    "The Second Doctor"
  ],
  "Jamie McCrimmon / The Seventh Doctor": [
    "Jamie McCrimmon",
    "The Seventh Doctor"
  ],
  "Jamie McCrimmon / The Sixth Doctor": [
    "Jamie McCrimmon",
    "The Sixth Doctor"
  ],
  "Jamie McCrimmon / The Tenth Doctor": [
    "Jamie McCrimmon",
    "The Tenth Doctor"
  ],
  "Jamie McCrimmon / The Third Doctor": [
    "Jamie McCrimmon",
    "The Third Doctor"
  ],
  "Jamie McCrimmon / The Thirteenth Doctor": [
    "Jamie McCrimmon",
    "The Thirteenth Doctor"
  ],
  "Jamie McCrimmon / The Twelfth Doctor": [
    "Jamie McCrimmon",
    "The Twelfth Doctor"
  ],
  "Jamie McCrimmon / The War Doctor": [
    "Jamie McCrimmon",
    "The War Doctor"
  ],
  "Jenny Flint / Madame Vastra": [
    "Jenny Flint",
    "Madame Vastra"
  ],
  "Jeska, Thrice Reborn / Kamahl, Heart of Krosa": [
    "Jeska, Thrice Reborn",
    "Kamahl, Heart of Krosa"
  ],
  "Jeska, Thrice Reborn / Kediss, Emberclaw Familiar": [
    "Jeska, Thrice Reborn",
    "Kediss, Emberclaw Familiar"
  ],
  "Jeska, Thrice Reborn / Keleth, Sunmane Familiar": [
    "Jeska, Thrice Reborn",
    "Keleth, Sunmane Familiar"
  ],
  "Jeska, Thrice Reborn / Keskit, the Flesh Sculptor": [
    "Jeska, Thrice Reborn",
    "Keskit, the Flesh Sculptor"
  ],
  "Jeska, Thrice Reborn / Kodama of the East Tree": [
    "Jeska, Thrice Reborn",
    "Kodama of the East Tree"
  ],
  "Jeska, Thrice Reborn / Krark, the Thumbless": [
    "Jeska, Thrice Reborn",
    "Krark, the Thumbless"
  ],
  "Jeska, Thrice Reborn / Kraum, Ludevic's Opus": [
    "Jeska, Thrice Reborn",
    "Kraum, Ludevic's Opus"
  ],
  "Jeska, Thrice Reborn / Kydele, Chosen of Kruphix": [
    "Jeska, Thrice Reborn",
    "Kydele, Chosen of Kruphix"
  ],
  "Jeska, Thrice Reborn / Livio, Oathsworn Sentinel": [
    "Jeska, Thrice Reborn",
    "Livio, Oathsworn Sentinel"
  ],
  "Jeska, Thrice Reborn / Ludevic, Necro-Alchemist": [
    "Jeska, Thrice Reborn",
    "Ludevic, Necro-Alchemist"
  ],
  "Jeska, Thrice Reborn / Malcolm, Keen-Eyed Navigator": [
    "Jeska, Thrice Reborn",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Jeska, Thrice Reborn / Miara, Thorn of the Glade": [
    "Jeska, Thrice Reborn",
    "Miara, Thorn of the Glade"
  ],
  "Jeska, Thrice Reborn / Nadier, Agent of the Duskenel": [
    "Jeska, Thrice Reborn",
    "Nadier, Agent of the Duskenel"
  ],
  "Jeska, Thrice Reborn / Numa, Joraga Chieftain": [
    "Jeska, Thrice Reborn",
    "Numa, Joraga Chieftain"
  ],
  "Jeska, Thrice Reborn / Prava of the Steel Legion": [
    "Jeska, Thrice Reborn",
    "Prava of the Steel Legion"
  ],
  "Jeska, Thrice Reborn / Radiant, Serra Archangel": [
    "Jeska, Thrice Reborn",
    "Radiant, Serra Archangel"
  ],
  "Jeska, Thrice Reborn / Ravos, Soultender": [
    "Jeska, Thrice Reborn",
    "Ravos, Soultender"
  ],
  "Jeska, Thrice Reborn / Rebbec, Architect of Ascension": [
    "Jeska, Thrice Reborn",
    "Rebbec, Architect of Ascension"
  ],
  "Jeska, Thrice Reborn / Reyhan, Last of the Abzan": [
    "Jeska, Thrice Reborn",
    "Reyhan, Last of the Abzan"
  ],
  "Jeska, Thrice Reborn / Rograkh, Son of Rohgahh": [
    "Jeska, Thrice Reborn",
    "Rograkh, Son of Rohgahh"
  ],
  "Jeska, Thrice Reborn / Sakashima of a Thousand Faces": [
    "Jeska, Thrice Reborn",
    "Sakashima of a Thousand Faces"
  ],
  "Jeska, Thrice Reborn / Sengir, the Dark Baron": [
    "Jeska, Thrice Reborn",
    "Sengir, the Dark Baron"
  ],
  "Jeska, Thrice Reborn / Siani, Eye of the Storm": [
    "Jeska, Thrice Reborn",
    "Siani, Eye of the Storm"
  ],
  "Jeska, Thrice Reborn / Sidar Kondo of Jamuraa": [
    "Jeska, Thrice Reborn",
    "Sidar Kondo of Jamuraa"
  ],
  "Jeska, Thrice Reborn / Silas Renn, Seeker Adept": [
    "Jeska, Thrice Reborn",
    "Silas Renn, Seeker Adept"
  ],
  "Jeska, Thrice Reborn / Slurrk, All-Ingesting": [
    "Jeska, Thrice Reborn",
    "Slurrk, All-Ingesting"
  ],
  "Jeska, Thrice Reborn / Tana, the Bloodsower": [
    "Jeska, Thrice Reborn",
    "Tana, the Bloodsower"
  ],
  "Jeska, Thrice Reborn / Tevesh Szat, Doom of Fools": [
    "Jeska, Thrice Reborn",
    "Tevesh Szat, Doom of Fools"
  ],
  "Jeska, Thrice Reborn / The Prismatic Piper": [
    "Jeska, Thrice Reborn",
    "The Prismatic Piper"
  ],
  "Jeska, Thrice Reborn / Thrasios, Triton Hero": [
    "Jeska, Thrice Reborn",
    "Thrasios, Triton Hero"
  ],
  "Jeska, Thrice Reborn / Toggo, Goblin Weaponsmith": [
    "Jeska, Thrice Reborn",
    "Toggo, Goblin Weaponsmith"
  ],
  "Jeska, Thrice Reborn / Tormod, the Desecrator": [
    "Jeska, Thrice Reborn",
    "Tormod, the Desecrator"
  ],
  "Jeska, Thrice Reborn / Tymna the Weaver": [
    "Jeska, Thrice Reborn",
    "Tymna the Weaver"
  ],
  "Jeska, Thrice Reborn / Vial Smasher the Fierce": [
    "Jeska, Thrice Reborn",
    "Vial Smasher the Fierce"
  ],
  "Jeska, Thrice Reborn / Yoshimaru, Ever Faithful": [
    "Jeska, Thrice Reborn",
    "Yoshimaru, Ever Faithful"
  ],
  "Jo Grant / The Eighth Doctor": [
    "Jo Grant",
    "The Eighth Doctor"
  ],
  "Jo Grant / The Eleventh Doctor": [
    "Jo Grant",
    "The Eleventh Doctor"
  ],
  "Jo Grant / The Fifteenth Doctor": [
    "Jo Grant",
    "The Fifteenth Doctor"
  ],
  "Jo Grant / The Fifth Doctor": [
    "Jo Grant",
    "The Fifth Doctor"
  ],
  "Jo Grant / The First Doctor": [
    "Jo Grant",
    "The First Doctor"
  ],
  "Jo Grant / The Fourteenth Doctor": [
    "Jo Grant",
    "The Fourteenth Doctor"
  ],
  "Jo Grant / The Fourth Doctor": [
    "Jo Grant",
    "The Fourth Doctor"
  ],
  "Jo Grant / The Fugitive Doctor": [
    "Jo Grant",
    "The Fugitive Doctor"
  ],
  "Jo Grant / The Ninth Doctor": [
    "Jo Grant",
    "The Ninth Doctor"
  ],
  "Jo Grant / The Second Doctor": [
    "Jo Grant",
    "The Second Doctor"
  ],
  "Jo Grant / The Seventh Doctor": [
    "Jo Grant",
    "The Seventh Doctor"
  ],
  "Jo Grant / The Sixth Doctor": [
    "Jo Grant",
    "The Sixth Doctor"
  ],
  "Jo Grant / The Tenth Doctor": [
    "Jo Grant",
    "The Tenth Doctor"
  ],
  "Jo Grant / The Third Doctor": [
    "Jo Grant",
    "The Third Doctor"
  ],
  "Jo Grant / The Thirteenth Doctor": [
    "Jo Grant",
    "The Thirteenth Doctor"
  ],
  "Jo Grant / The Twelfth Doctor": [
    "Jo Grant",
    "The Twelfth Doctor"
  ],
  "Jo Grant / The War Doctor": [
    "Jo Grant",
    "The War Doctor"
  ],
  "K-9, Mark I / The Eighth Doctor": [
    "K-9, Mark I",
    "The Eighth Doctor"
  ],
  "K-9, Mark I / The Eleventh Doctor": [
    "K-9, Mark I",
    "The Eleventh Doctor"
  ],
  "K-9, Mark I / The Fifteenth Doctor": [
    "K-9, Mark I",
    "The Fifteenth Doctor"
  ],
  "K-9, Mark I / The Fifth Doctor": [
    "K-9, Mark I",
    "The Fifth Doctor"
  ],
  "K-9, Mark I / The First Doctor": [
    "K-9, Mark I",
    "The First Doctor"
  ],
  "K-9, Mark I / The Fourteenth Doctor": [
    "K-9, Mark I",
    "The Fourteenth Doctor"
  ],
  "K-9, Mark I / The Fourth Doctor": [
    "K-9, Mark I",
    "The Fourth Doctor"
  ],
  "K-9, Mark I / The Fugitive Doctor": [
    "K-9, Mark I",
    "The Fugitive Doctor"
  ],
  "K-9, Mark I / The Ninth Doctor": [
    "K-9, Mark I",
    "The Ninth Doctor"
  ],
  "K-9, Mark I / The Second Doctor": [
    "K-9, Mark I",
    "The Second Doctor"
  ],
  "K-9, Mark I / The Seventh Doctor": [
    "K-9, Mark I",
    "The Seventh Doctor"
  ],
  "K-9, Mark I / The Sixth Doctor": [
    "K-9, Mark I",
    "The Sixth Doctor"
  ],
  "K-9, Mark I / The Tenth Doctor": [
    "K-9, Mark I",
    "The Tenth Doctor"
  ],
  "K-9, Mark I / The Third Doctor": [
    "K-9, Mark I",
    "The Third Doctor"
  ],
  "K-9, Mark I / The Thirteenth Doctor": [
    "K-9, Mark I",
    "The Thirteenth Doctor"
  ],
  "K-9, Mark I / The Twelfth Doctor": [
    "K-9, Mark I",
    "The Twelfth Doctor"
  ],
  "K-9, Mark I / The War Doctor": [
    "K-9, Mark I",
    "The War Doctor"
  ],
  "Kamahl, Heart of Krosa / Kediss, Emberclaw Familiar": [
    "Kamahl, Heart of Krosa",
    "Kediss, Emberclaw Familiar"
  ],
  "Kamahl, Heart of Krosa / Keleth, Sunmane Familiar": [
    "Kamahl, Heart of Krosa",
    "Keleth, Sunmane Familiar"
  ],
  "Kamahl, Heart of Krosa / Keskit, the Flesh Sculptor": [
    "Kamahl, Heart of Krosa",
    "Keskit, the Flesh Sculptor"
  ],
  "Kamahl, Heart of Krosa / Kodama of the East Tree": [
    "Kamahl, Heart of Krosa",
    "Kodama of the East Tree"
  ],
  "Kamahl, Heart of Krosa / Krark, the Thumbless": [
    "Kamahl, Heart of Krosa",
    "Krark, the Thumbless"
  ],
  "Kamahl, Heart of Krosa / Kraum, Ludevic's Opus": [
    "Kamahl, Heart of Krosa",
    "Kraum, Ludevic's Opus"
  ],
  "Kamahl, Heart of Krosa / Kydele, Chosen of Kruphix": [
    "Kamahl, Heart of Krosa",
    "Kydele, Chosen of Kruphix"
  ],
  "Kamahl, Heart of Krosa / Livio, Oathsworn Sentinel": [
    "Kamahl, Heart of Krosa",
    "Livio, Oathsworn Sentinel"
  ],
  "Kamahl, Heart of Krosa / Ludevic, Necro-Alchemist": [
    "Kamahl, Heart of Krosa",
    "Ludevic, Necro-Alchemist"
  ],
  "Kamahl, Heart of Krosa / Malcolm, Keen-Eyed Navigator": [
    "Kamahl, Heart of Krosa",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Kamahl, Heart of Krosa / Miara, Thorn of the Glade": [
    "Kamahl, Heart of Krosa",
    "Miara, Thorn of the Glade"
  ],
  "Kamahl, Heart of Krosa / Nadier, Agent of the Duskenel": [
    "Kamahl, Heart of Krosa",
    "Nadier, Agent of the Duskenel"
  ],
  "Kamahl, Heart of Krosa / Numa, Joraga Chieftain": [
    "Kamahl, Heart of Krosa",
    "Numa, Joraga Chieftain"
  ],
  "Kamahl, Heart of Krosa / Prava of the Steel Legion": [
    "Kamahl, Heart of Krosa",
    "Prava of the Steel Legion"
  ],
  "Kamahl, Heart of Krosa / Radiant, Serra Archangel": [
    "Kamahl, Heart of Krosa",
    "Radiant, Serra Archangel"
  ],
  "Kamahl, Heart of Krosa / Ravos, Soultender": [
    "Kamahl, Heart of Krosa",
    "Ravos, Soultender"
  ],
  "Kamahl, Heart of Krosa / Rebbec, Architect of Ascension": [
    "Kamahl, Heart of Krosa",
    "Rebbec, Architect of Ascension"
  ],
  "Kamahl, Heart of Krosa / Reyhan, Last of the Abzan": [
    "Kamahl, Heart of Krosa",
    "Reyhan, Last of the Abzan"
  ],
  "Kamahl, Heart of Krosa / Rograkh, Son of Rohgahh": [
    "Kamahl, Heart of Krosa",
    "Rograkh, Son of Rohgahh"
  ],
  "Kamahl, Heart of Krosa / Sakashima of a Thousand Faces": [
    "Kamahl, Heart of Krosa",
    "Sakashima of a Thousand Faces"
  ],
  "Kamahl, Heart of Krosa / Sengir, the Dark Baron": [
    "Kamahl, Heart of Krosa",
    "Sengir, the Dark Baron"
  ],
  "Kamahl, Heart of Krosa / Siani, Eye of the Storm": [
    "Kamahl, Heart of Krosa",
    "Siani, Eye of the Storm"
  ],
  "Kamahl, Heart of Krosa / Sidar Kondo of Jamuraa": [
    "Kamahl, Heart of Krosa",
    "Sidar Kondo of Jamuraa"
  ],
  "Kamahl, Heart of Krosa / Silas Renn, Seeker Adept": [
    "Kamahl, Heart of Krosa",
    "Silas Renn, Seeker Adept"
  ],
  "Kamahl, Heart of Krosa / Slurrk, All-Ingesting": [
    "Kamahl, Heart of Krosa",
    "Slurrk, All-Ingesting"
  ],
  "Kamahl, Heart of Krosa / Tana, the Bloodsower": [
    "Kamahl, Heart of Krosa",
    "Tana, the Bloodsower"
  ],
  "Kamahl, Heart of Krosa / Tevesh Szat, Doom of Fools": [
    "Kamahl, Heart of Krosa",
    "Tevesh Szat, Doom of Fools"
  ],
  "Kamahl, Heart of Krosa / The Prismatic Piper": [
    "Kamahl, Heart of Krosa",
    "The Prismatic Piper"
  ],
  "Kamahl, Heart of Krosa / Thrasios, Triton Hero": [
    "Kamahl, Heart of Krosa",
    "Thrasios, Triton Hero"
  ],
  "Kamahl, Heart of Krosa / Toggo, Goblin Weaponsmith": [
    "Kamahl, Heart of Krosa",
    "Toggo, Goblin Weaponsmith"
  ],
  "Kamahl, Heart of Krosa / Tormod, the Desecrator": [
    "Kamahl, Heart of Krosa",
    "Tormod, the Desecrator"
  ],
  "Kamahl, Heart of Krosa / Tymna the Weaver": [
    "Kamahl, Heart of Krosa",
    "Tymna the Weaver"
  ],
  "Kamahl, Heart of Krosa / Vial Smasher the Fierce": [
    "Kamahl, Heart of Krosa",
    "Vial Smasher the Fierce"
  ],
  "Kamahl, Heart of Krosa / Yoshimaru, Ever Faithful": [
    "Kamahl, Heart of Krosa",
    "Yoshimaru, Ever Faithful"
  ],
  "Kamber, the Plunderer / Laurine, the Diversion": [
    "Kamber, the Plunderer",
    "Laurine, the Diversion"
  ],
  "Karlach, Fury of Avernus / Master Chef": [
    "Karlach, Fury of Avernus",
    "Master Chef"
  ],
  "Karlach, Fury of Avernus / Noble Heritage": [
    "Karlach, Fury of Avernus",
    "Noble Heritage"
  ],
  "Karlach, Fury of Avernus / Passionate Archaeologist": [
    "Karlach, Fury of Avernus",
    "Passionate Archaeologist"
  ],
  "Karlach, Fury of Avernus / Popular Entertainer": [
    "Karlach, Fury of Avernus",
    "Popular Entertainer"
  ],
  "Karlach, Fury of Avernus / Raised by Giants": [
    "Karlach, Fury of Avernus",
    "Raised by Giants"
  ],
  "Karlach, Fury of Avernus / Scion of Halaster": [
    "Karlach, Fury of Avernus",
    "Scion of Halaster"
  ],
  "Karlach, Fury of Avernus / Shameless Charlatan": [
    "Karlach, Fury of Avernus",
    "Shameless Charlatan"
  ],
  "Karlach, Fury of Avernus / Street Urchin": [
    "Karlach, Fury of Avernus",
    "Street Urchin"
  ],
  "Karlach, Fury of Avernus / Sword Coast Sailor": [
    "Karlach, Fury of Avernus",
    "Sword Coast Sailor"
  ],
  "Karlach, Fury of Avernus / Tavern Brawler": [
    "Karlach, Fury of Avernus",
    "Tavern Brawler"
  ],
  "Karlach, Fury of Avernus / Veteran Soldier": [
    "Karlach, Fury of Avernus",
    "Veteran Soldier"
  ],
  "Kediss, Emberclaw Familiar / Keleth, Sunmane Familiar": [
    "Kediss, Emberclaw Familiar",
    "Keleth, Sunmane Familiar"
  ],
  "Kediss, Emberclaw Familiar / Keskit, the Flesh Sculptor": [
    "Kediss, Emberclaw Familiar",
    "Keskit, the Flesh Sculptor"
  ],
  "Kediss, Emberclaw Familiar / Kodama of the East Tree": [
    "Kediss, Emberclaw Familiar",
    "Kodama of the East Tree"
  ],
  "Kediss, Emberclaw Familiar / Krark, the Thumbless": [
    "Kediss, Emberclaw Familiar",
    "Krark, the Thumbless"
  ],
  "Kediss, Emberclaw Familiar / Kraum, Ludevic's Opus": [
    "Kediss, Emberclaw Familiar",
    "Kraum, Ludevic's Opus"
  ],
  "Kediss, Emberclaw Familiar / Kydele, Chosen of Kruphix": [
    "Kediss, Emberclaw Familiar",
    "Kydele, Chosen of Kruphix"
  ],
  "Kediss, Emberclaw Familiar / Livio, Oathsworn Sentinel": [
    "Kediss, Emberclaw Familiar",
    "Livio, Oathsworn Sentinel"
  ],
  "Kediss, Emberclaw Familiar / Ludevic, Necro-Alchemist": [
    "Kediss, Emberclaw Familiar",
    "Ludevic, Necro-Alchemist"
  ],
  "Kediss, Emberclaw Familiar / Malcolm, Keen-Eyed Navigator": [
    "Malcolm, Keen-Eyed Navigator",
    "Kediss, Emberclaw Familiar"
  ],
  "Kediss, Emberclaw Familiar / Miara, Thorn of the Glade": [
    "Kediss, Emberclaw Familiar",
    "Miara, Thorn of the Glade"
  ],
  "Kediss, Emberclaw Familiar / Nadier, Agent of the Duskenel": [
    "Kediss, Emberclaw Familiar",
    "Nadier, Agent of the Duskenel"
  ],
  "Kediss, Emberclaw Familiar / Numa, Joraga Chieftain": [
    "Kediss, Emberclaw Familiar",
    "Numa, Joraga Chieftain"
  ],
  "Kediss, Emberclaw Familiar / Prava of the Steel Legion": [
    "Kediss, Emberclaw Familiar",
    "Prava of the Steel Legion"
  ],
  "Kediss, Emberclaw Familiar / Radiant, Serra Archangel": [
    "Kediss, Emberclaw Familiar",
    "Radiant, Serra Archangel"
  ],
  "Kediss, Emberclaw Familiar / Ravos, Soultender": [
    "Kediss, Emberclaw Familiar",
    "Ravos, Soultender"
  ],
  "Kediss, Emberclaw Familiar / Rebbec, Architect of Ascension": [
    "Kediss, Emberclaw Familiar",
    "Rebbec, Architect of Ascension"
  ],
  "Kediss, Emberclaw Familiar / Reyhan, Last of the Abzan": [
    "Kediss, Emberclaw Familiar",
    "Reyhan, Last of the Abzan"
  ],
  "Kediss, Emberclaw Familiar / Rograkh, Son of Rohgahh": [
    "Kediss, Emberclaw Familiar",
    "Rograkh, Son of Rohgahh"
  ],
  "Kediss, Emberclaw Familiar / Sakashima of a Thousand Faces": [
    "Kediss, Emberclaw Familiar",
    "Sakashima of a Thousand Faces"
  ],
  "Kediss, Emberclaw Familiar / Sengir, the Dark Baron": [
    "Kediss, Emberclaw Familiar",
    "Sengir, the Dark Baron"
  ],
  "Kediss, Emberclaw Familiar / Siani, Eye of the Storm": [
    "Kediss, Emberclaw Familiar",
    "Siani, Eye of the Storm"
  ],
  "Kediss, Emberclaw Familiar / Sidar Kondo of Jamuraa": [
    "Kediss, Emberclaw Familiar",
    "Sidar Kondo of Jamuraa"
  ],
  "Kediss, Emberclaw Familiar / Silas Renn, Seeker Adept": [
    "Kediss, Emberclaw Familiar",
    "Silas Renn, Seeker Adept"
  ],
  "Kediss, Emberclaw Familiar / Slurrk, All-Ingesting": [
    "Kediss, Emberclaw Familiar",
    "Slurrk, All-Ingesting"
  ],
  "Kediss, Emberclaw Familiar / Tana, the Bloodsower": [
    "Kediss, Emberclaw Familiar",
    "Tana, the Bloodsower"
  ],
  "Kediss, Emberclaw Familiar / Tevesh Szat, Doom of Fools": [
    "Kediss, Emberclaw Familiar",
    "Tevesh Szat, Doom of Fools"
  ],
  "Kediss, Emberclaw Familiar / The Prismatic Piper": [
    "Kediss, Emberclaw Familiar",
    "The Prismatic Piper"
  ],
  "Kediss, Emberclaw Familiar / Thrasios, Triton Hero": [
    "Kediss, Emberclaw Familiar",
    "Thrasios, Triton Hero"
  ],
  "Kediss, Emberclaw Familiar / Toggo, Goblin Weaponsmith": [
    "Kediss, Emberclaw Familiar",
    "Toggo, Goblin Weaponsmith"
  ],
  "Kediss, Emberclaw Familiar / Tormod, the Desecrator": [
    "Kediss, Emberclaw Familiar",
    "Tormod, the Desecrator"
  ],
  "Kediss, Emberclaw Familiar / Tymna the Weaver": [
    "Kediss, Emberclaw Familiar",
    "Tymna the Weaver"
  ],
  "Kediss, Emberclaw Familiar / Vial Smasher the Fierce": [
    "Kediss, Emberclaw Familiar",
    "Vial Smasher the Fierce"
  ],
  "Kediss, Emberclaw Familiar / Yoshimaru, Ever Faithful": [
    "Kediss, Emberclaw Familiar",
    "Yoshimaru, Ever Faithful"
  ],
  "Keleth, Sunmane Familiar / Keskit, the Flesh Sculptor": [
    "Keleth, Sunmane Familiar",
    "Keskit, the Flesh Sculptor"
  ],
  "Keleth, Sunmane Familiar / Kodama of the East Tree": [
    "Keleth, Sunmane Familiar",
    "Kodama of the East Tree"
  ],
  "Keleth, Sunmane Familiar / Krark, the Thumbless": [
    "Keleth, Sunmane Familiar",
    "Krark, the Thumbless"
  ],
  "Keleth, Sunmane Familiar / Kraum, Ludevic's Opus": [
    "Keleth, Sunmane Familiar",
    "Kraum, Ludevic's Opus"
  ],
  "Keleth, Sunmane Familiar / Kydele, Chosen of Kruphix": [
    "Keleth, Sunmane Familiar",
    "Kydele, Chosen of Kruphix"
  ],
  "Keleth, Sunmane Familiar / Livio, Oathsworn Sentinel": [
    "Keleth, Sunmane Familiar",
    "Livio, Oathsworn Sentinel"
  ],
  "Keleth, Sunmane Familiar / Ludevic, Necro-Alchemist": [
    "Keleth, Sunmane Familiar",
    "Ludevic, Necro-Alchemist"
  ],
  "Keleth, Sunmane Familiar / Malcolm, Keen-Eyed Navigator": [
    "Keleth, Sunmane Familiar",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Keleth, Sunmane Familiar / Miara, Thorn of the Glade": [
    "Keleth, Sunmane Familiar",
    "Miara, Thorn of the Glade"
  ],
  "Keleth, Sunmane Familiar / Nadier, Agent of the Duskenel": [
    "Keleth, Sunmane Familiar",
    "Nadier, Agent of the Duskenel"
  ],
  "Keleth, Sunmane Familiar / Numa, Joraga Chieftain": [
    "Keleth, Sunmane Familiar",
    "Numa, Joraga Chieftain"
  ],
  "Keleth, Sunmane Familiar / Prava of the Steel Legion": [
    "Keleth, Sunmane Familiar",
    "Prava of the Steel Legion"
  ],
  "Keleth, Sunmane Familiar / Radiant, Serra Archangel": [
    "Keleth, Sunmane Familiar",
    "Radiant, Serra Archangel"
  ],
  "Keleth, Sunmane Familiar / Ravos, Soultender": [
    "Keleth, Sunmane Familiar",
    "Ravos, Soultender"
  ],
  "Keleth, Sunmane Familiar / Rebbec, Architect of Ascension": [
    "Keleth, Sunmane Familiar",
    "Rebbec, Architect of Ascension"
  ],
  "Keleth, Sunmane Familiar / Reyhan, Last of the Abzan": [
    "Keleth, Sunmane Familiar",
    "Reyhan, Last of the Abzan"
  ],
  "Keleth, Sunmane Familiar / Rograkh, Son of Rohgahh": [
    "Keleth, Sunmane Familiar",
    "Rograkh, Son of Rohgahh"
  ],
  "Keleth, Sunmane Familiar / Sakashima of a Thousand Faces": [
    "Keleth, Sunmane Familiar",
    "Sakashima of a Thousand Faces"
  ],
  "Keleth, Sunmane Familiar / Sengir, the Dark Baron": [
    "Keleth, Sunmane Familiar",
    "Sengir, the Dark Baron"
  ],
  "Keleth, Sunmane Familiar / Siani, Eye of the Storm": [
    "Keleth, Sunmane Familiar",
    "Siani, Eye of the Storm"
  ],
  "Keleth, Sunmane Familiar / Sidar Kondo of Jamuraa": [
    "Keleth, Sunmane Familiar",
    "Sidar Kondo of Jamuraa"
  ],
  "Keleth, Sunmane Familiar / Silas Renn, Seeker Adept": [
    "Keleth, Sunmane Familiar",
    "Silas Renn, Seeker Adept"
  ],
  "Keleth, Sunmane Familiar / Slurrk, All-Ingesting": [
    "Keleth, Sunmane Familiar",
    "Slurrk, All-Ingesting"
  ],
  "Keleth, Sunmane Familiar / Tana, the Bloodsower": [
    "Keleth, Sunmane Familiar",
    "Tana, the Bloodsower"
  ],
  "Keleth, Sunmane Familiar / Tevesh Szat, Doom of Fools": [
    "Keleth, Sunmane Familiar",
    "Tevesh Szat, Doom of Fools"
  ],
  "Keleth, Sunmane Familiar / The Prismatic Piper": [
    "Keleth, Sunmane Familiar",
    "The Prismatic Piper"
  ],
  "Keleth, Sunmane Familiar / Thrasios, Triton Hero": [
    "Keleth, Sunmane Familiar",
    "Thrasios, Triton Hero"
  ],
  "Keleth, Sunmane Familiar / Toggo, Goblin Weaponsmith": [
    "Keleth, Sunmane Familiar",
    "Toggo, Goblin Weaponsmith"
  ],
  "Keleth, Sunmane Familiar / Tormod, the Desecrator": [
    "Keleth, Sunmane Familiar",
    "Tormod, the Desecrator"
  ],
  "Keleth, Sunmane Familiar / Tymna the Weaver": [
    "Keleth, Sunmane Familiar",
    "Tymna the Weaver"
  ],
  "Keleth, Sunmane Familiar / Vial Smasher the Fierce": [
    "Keleth, Sunmane Familiar",
    "Vial Smasher the Fierce"
  ],
  "Keleth, Sunmane Familiar / Yoshimaru, Ever Faithful": [
    "Keleth, Sunmane Familiar",
    "Yoshimaru, Ever Faithful"
  ],
  "Keskit, the Flesh Sculptor / Kodama of the East Tree": [
    "Keskit, the Flesh Sculptor",
    "Kodama of the East Tree"
  ],
  "Keskit, the Flesh Sculptor / Krark, the Thumbless": [
    "Keskit, the Flesh Sculptor",
    "Krark, the Thumbless"
  ],
  "Keskit, the Flesh Sculptor / Kraum, Ludevic's Opus": [
    "Keskit, the Flesh Sculptor",
    "Kraum, Ludevic's Opus"
  ],
  "Keskit, the Flesh Sculptor / Kydele, Chosen of Kruphix": [
    "Keskit, the Flesh Sculptor",
    "Kydele, Chosen of Kruphix"
  ],
  "Keskit, the Flesh Sculptor / Livio, Oathsworn Sentinel": [
    "Keskit, the Flesh Sculptor",
    "Livio, Oathsworn Sentinel"
  ],
  "Keskit, the Flesh Sculptor / Ludevic, Necro-Alchemist": [
    "Keskit, the Flesh Sculptor",
    "Ludevic, Necro-Alchemist"
  ],
  "Keskit, the Flesh Sculptor / Malcolm, Keen-Eyed Navigator": [
    "Keskit, the Flesh Sculptor",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Keskit, the Flesh Sculptor / Miara, Thorn of the Glade": [
    "Keskit, the Flesh Sculptor",
    "Miara, Thorn of the Glade"
  ],
  "Keskit, the Flesh Sculptor / Nadier, Agent of the Duskenel": [
    "Keskit, the Flesh Sculptor",
    "Nadier, Agent of the Duskenel"
  ],
  "Keskit, the Flesh Sculptor / Numa, Joraga Chieftain": [
    "Keskit, the Flesh Sculptor",
    "Numa, Joraga Chieftain"
  ],
  "Keskit, the Flesh Sculptor / Prava of the Steel Legion": [
    "Keskit, the Flesh Sculptor",
    "Prava of the Steel Legion"
  ],
  "Keskit, the Flesh Sculptor / Radiant, Serra Archangel": [
    "Keskit, the Flesh Sculptor",
    "Radiant, Serra Archangel"
  ],
  "Keskit, the Flesh Sculptor / Ravos, Soultender": [
    "Keskit, the Flesh Sculptor",
    "Ravos, Soultender"
  ],
  "Keskit, the Flesh Sculptor / Rebbec, Architect of Ascension": [
    "Keskit, the Flesh Sculptor",
    "Rebbec, Architect of Ascension"
  ],
  "Keskit, the Flesh Sculptor / Reyhan, Last of the Abzan": [
    "Keskit, the Flesh Sculptor",
    "Reyhan, Last of the Abzan"
  ],
  "Keskit, the Flesh Sculptor / Rograkh, Son of Rohgahh": [
    "Keskit, the Flesh Sculptor",
    "Rograkh, Son of Rohgahh"
  ],
  "Keskit, the Flesh Sculptor / Sakashima of a Thousand Faces": [
    "Keskit, the Flesh Sculptor",
    "Sakashima of a Thousand Faces"
  ],
  "Keskit, the Flesh Sculptor / Sengir, the Dark Baron": [
    "Keskit, the Flesh Sculptor",
    "Sengir, the Dark Baron"
  ],
  "Keskit, the Flesh Sculptor / Siani, Eye of the Storm": [
    "Keskit, the Flesh Sculptor",
    "Siani, Eye of the Storm"
  ],
  "Keskit, the Flesh Sculptor / Sidar Kondo of Jamuraa": [
    "Keskit, the Flesh Sculptor",
    "Sidar Kondo of Jamuraa"
  ],
  "Keskit, the Flesh Sculptor / Silas Renn, Seeker Adept": [
    "Keskit, the Flesh Sculptor",
    "Silas Renn, Seeker Adept"
  ],
  "Keskit, the Flesh Sculptor / Slurrk, All-Ingesting": [
    "Keskit, the Flesh Sculptor",
    "Slurrk, All-Ingesting"
  ],
  "Keskit, the Flesh Sculptor / Tana, the Bloodsower": [
    "Keskit, the Flesh Sculptor",
    "Tana, the Bloodsower"
  ],
  "Keskit, the Flesh Sculptor / Tevesh Szat, Doom of Fools": [
    "Keskit, the Flesh Sculptor",
    "Tevesh Szat, Doom of Fools"
  ],
  "Keskit, the Flesh Sculptor / The Prismatic Piper": [
    "Keskit, the Flesh Sculptor",
    "The Prismatic Piper"
  ],
  "Keskit, the Flesh Sculptor / Thrasios, Triton Hero": [
    "Keskit, the Flesh Sculptor",
    "Thrasios, Triton Hero"
  ],
  "Keskit, the Flesh Sculptor / Toggo, Goblin Weaponsmith": [
    "Keskit, the Flesh Sculptor",
    "Toggo, Goblin Weaponsmith"
  ],
  "Keskit, the Flesh Sculptor / Tormod, the Desecrator": [
    "Keskit, the Flesh Sculptor",
    "Tormod, the Desecrator"
  ],
  "Keskit, the Flesh Sculptor / Tymna the Weaver": [
    "Keskit, the Flesh Sculptor",
    "Tymna the Weaver"
  ],
  "Keskit, the Flesh Sculptor / Vial Smasher the Fierce": [
    "Keskit, the Flesh Sculptor",
    "Vial Smasher the Fierce"
  ],
  "Keskit, the Flesh Sculptor / Yoshimaru, Ever Faithful": [
    "Keskit, the Flesh Sculptor",
    "Yoshimaru, Ever Faithful"
  ],
  "Khorvath Brightflame / Sylvia Brightspear": [
    "Khorvath Brightflame",
    "Sylvia Brightspear"
  ],
  "Kodama of the East Tree / Krark, the Thumbless": [
    "Kodama of the East Tree",
    "Krark, the Thumbless"
  ],
  "Kodama of the East Tree / Kraum, Ludevic's Opus": [
    "Kodama of the East Tree",
    "Kraum, Ludevic's Opus"
  ],
  "Kodama of the East Tree / Kydele, Chosen of Kruphix": [
    "Kodama of the East Tree",
    "Kydele, Chosen of Kruphix"
  ],
  "Kodama of the East Tree / Livio, Oathsworn Sentinel": [
    "Kodama of the East Tree",
    "Livio, Oathsworn Sentinel"
  ],
  "Kodama of the East Tree / Ludevic, Necro-Alchemist": [
    "Kodama of the East Tree",
    "Ludevic, Necro-Alchemist"
  ],
  "Kodama of the East Tree / Malcolm, Keen-Eyed Navigator": [
    "Kodama of the East Tree",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Kodama of the East Tree / Miara, Thorn of the Glade": [
    "Kodama of the East Tree",
    "Miara, Thorn of the Glade"
  ],
  "Kodama of the East Tree / Nadier, Agent of the Duskenel": [
    "Kodama of the East Tree",
    "Nadier, Agent of the Duskenel"
  ],
  "Kodama of the East Tree / Numa, Joraga Chieftain": [
    "Kodama of the East Tree",
    "Numa, Joraga Chieftain"
  ],
  "Kodama of the East Tree / Prava of the Steel Legion": [
    "Kodama of the East Tree",
    "Prava of the Steel Legion"
  ],
  "Kodama of the East Tree / Radiant, Serra Archangel": [
    "Kodama of the East Tree",
    "Radiant, Serra Archangel"
  ],
  "Kodama of the East Tree / Ravos, Soultender": [
    "Kodama of the East Tree",
    "Ravos, Soultender"
  ],
  "Kodama of the East Tree / Rebbec, Architect of Ascension": [
    "Kodama of the East Tree",
    "Rebbec, Architect of Ascension"
  ],
  "Kodama of the East Tree / Reyhan, Last of the Abzan": [
    "Kodama of the East Tree",
    "Reyhan, Last of the Abzan"
  ],
  "Kodama of the East Tree / Rograkh, Son of Rohgahh": [
    "Kodama of the East Tree",
    "Rograkh, Son of Rohgahh"
  ],
  "Kodama of the East Tree / Sakashima of a Thousand Faces": [
    "Kodama of the East Tree",
    "Sakashima of a Thousand Faces"
  ],
  "Kodama of the East Tree / Sengir, the Dark Baron": [
    "Kodama of the East Tree",
    "Sengir, the Dark Baron"
  ],
  "Kodama of the East Tree / Siani, Eye of the Storm": [
    "Kodama of the East Tree",
    "Siani, Eye of the Storm"
  ],
  "Kodama of the East Tree / Sidar Kondo of Jamuraa": [
    "Kodama of the East Tree",
    "Sidar Kondo of Jamuraa"
  ],
  "Kodama of the East Tree / Silas Renn, Seeker Adept": [
    "Kodama of the East Tree",
    "Silas Renn, Seeker Adept"
  ],
  "Kodama of the East Tree / Slurrk, All-Ingesting": [
    "Kodama of the East Tree",
    "Slurrk, All-Ingesting"
  ],
  "Kodama of the East Tree / Tana, the Bloodsower": [
    "Kodama of the East Tree",
    "Tana, the Bloodsower"
  ],
  "Kodama of the East Tree / Tevesh Szat, Doom of Fools": [
    "Kodama of the East Tree",
    "Tevesh Szat, Doom of Fools"
  ],
  "Kodama of the East Tree / The Prismatic Piper": [
    "Kodama of the East Tree",
    "The Prismatic Piper"
  ],
  "Kodama of the East Tree / Thrasios, Triton Hero": [
    "Kodama of the East Tree",
    "Thrasios, Triton Hero"
  ],
  "Kodama of the East Tree / Toggo, Goblin Weaponsmith": [
    "Kodama of the East Tree",
    "Toggo, Goblin Weaponsmith"
  ],
  "Kodama of the East Tree / Tormod, the Desecrator": [
    "Kodama of the East Tree",
    "Tormod, the Desecrator"
  ],
  "Kodama of the East Tree / Tymna the Weaver": [
    "Kodama of the East Tree",
    "Tymna the Weaver"
  ],
  "Kodama of the East Tree / Vial Smasher the Fierce": [
    "Kodama of the East Tree",
    "Vial Smasher the Fierce"
  ],
  "Kodama of the East Tree / Yoshimaru, Ever Faithful": [
    "Kodama of the East Tree",
    "Yoshimaru, Ever Faithful"
  ],
  "Krark, the Thumbless / Kraum, Ludevic's Opus": [
    "Krark, the Thumbless",
    "Kraum, Ludevic's Opus"
  ],
  "Krark, the Thumbless / Kydele, Chosen of Kruphix": [
    "Krark, the Thumbless",
    "Kydele, Chosen of Kruphix"
  ],
  "Krark, the Thumbless / Livio, Oathsworn Sentinel": [
    "Krark, the Thumbless",
    "Livio, Oathsworn Sentinel"
  ],
  "Krark, the Thumbless / Ludevic, Necro-Alchemist": [
    "Krark, the Thumbless",
    "Ludevic, Necro-Alchemist"
  ],
  "Krark, the Thumbless / Malcolm, Keen-Eyed Navigator": [
    "Krark, the Thumbless",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Krark, the Thumbless / Miara, Thorn of the Glade": [
    "Krark, the Thumbless",
    "Miara, Thorn of the Glade"
  ],
  "Krark, the Thumbless / Nadier, Agent of the Duskenel": [
    "Krark, the Thumbless",
    "Nadier, Agent of the Duskenel"
  ],
  "Krark, the Thumbless / Numa, Joraga Chieftain": [
    "Krark, the Thumbless",
    "Numa, Joraga Chieftain"
  ],
  "Krark, the Thumbless / Prava of the Steel Legion": [
    "Krark, the Thumbless",
    "Prava of the Steel Legion"
  ],
  "Krark, the Thumbless / Radiant, Serra Archangel": [
    "Krark, the Thumbless",
    "Radiant, Serra Archangel"
  ],
  "Krark, the Thumbless / Ravos, Soultender": [
    "Krark, the Thumbless",
    "Ravos, Soultender"
  ],
  "Krark, the Thumbless / Rebbec, Architect of Ascension": [
    "Krark, the Thumbless",
    "Rebbec, Architect of Ascension"
  ],
  "Krark, the Thumbless / Reyhan, Last of the Abzan": [
    "Krark, the Thumbless",
    "Reyhan, Last of the Abzan"
  ],
  "Krark, the Thumbless / Rograkh, Son of Rohgahh": [
    "Krark, the Thumbless",
    "Rograkh, Son of Rohgahh"
  ],
  "Krark, the Thumbless / Sakashima of a Thousand Faces": [
    "Krark, the Thumbless",
    "Sakashima of a Thousand Faces"
  ],
  "Krark, the Thumbless / Sengir, the Dark Baron": [
    "Krark, the Thumbless",
    "Sengir, the Dark Baron"
  ],
  "Krark, the Thumbless / Siani, Eye of the Storm": [
    "Krark, the Thumbless",
    "Siani, Eye of the Storm"
  ],
  "Krark, the Thumbless / Sidar Kondo of Jamuraa": [
    "Krark, the Thumbless",
    "Sidar Kondo of Jamuraa"
  ],
  "Krark, the Thumbless / Silas Renn, Seeker Adept": [
    "Krark, the Thumbless",
    "Silas Renn, Seeker Adept"
  ],
  "Krark, the Thumbless / Slurrk, All-Ingesting": [
    "Krark, the Thumbless",
    "Slurrk, All-Ingesting"
  ],
  "Krark, the Thumbless / Tana, the Bloodsower": [
    "Krark, the Thumbless",
    "Tana, the Bloodsower"
  ],
  "Krark, the Thumbless / Tevesh Szat, Doom of Fools": [
    "Krark, the Thumbless",
    "Tevesh Szat, Doom of Fools"
  ],
  "Krark, the Thumbless / The Prismatic Piper": [
    "Krark, the Thumbless",
    "The Prismatic Piper"
  ],
  "Krark, the Thumbless / Thrasios, Triton Hero": [
    "Krark, the Thumbless",
    "Thrasios, Triton Hero"
  ],
  "Krark, the Thumbless / Toggo, Goblin Weaponsmith": [
    "Krark, the Thumbless",
    "Toggo, Goblin Weaponsmith"
  ],
  "Krark, the Thumbless / Tormod, the Desecrator": [
    "Krark, the Thumbless",
    "Tormod, the Desecrator"
  ],
  "Krark, the Thumbless / Tymna the Weaver": [
    "Krark, the Thumbless",
    "Tymna the Weaver"
  ],
  "Krark, the Thumbless / Vial Smasher the Fierce": [
    "Krark, the Thumbless",
    "Vial Smasher the Fierce"
  ],
  "Krark, the Thumbless / Yoshimaru, Ever Faithful": [
    "Krark, the Thumbless",
    "Yoshimaru, Ever Faithful"
  ],
  "Kraum, Ludevic's Opus / Kydele, Chosen of Kruphix": [
    "Kraum, Ludevic's Opus",
    "Kydele, Chosen of Kruphix"
  ],
  "Kraum, Ludevic's Opus / Livio, Oathsworn Sentinel": [
    "Kraum, Ludevic's Opus",
    "Livio, Oathsworn Sentinel"
  ],
  "Kraum, Ludevic's Opus / Ludevic, Necro-Alchemist": [
    "Kraum, Ludevic's Opus",
    "Ludevic, Necro-Alchemist"
  ],
  "Kraum, Ludevic's Opus / Malcolm, Keen-Eyed Navigator": [
    "Kraum, Ludevic's Opus",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Kraum, Ludevic's Opus / Miara, Thorn of the Glade": [
    "Kraum, Ludevic's Opus",
    "Miara, Thorn of the Glade"
  ],
  "Kraum, Ludevic's Opus / Nadier, Agent of the Duskenel": [
    "Kraum, Ludevic's Opus",
    "Nadier, Agent of the Duskenel"
  ],
  "Kraum, Ludevic's Opus / Numa, Joraga Chieftain": [
    "Kraum, Ludevic's Opus",
    "Numa, Joraga Chieftain"
  ],
  "Kraum, Ludevic's Opus / Prava of the Steel Legion": [
    "Kraum, Ludevic's Opus",
    "Prava of the Steel Legion"
  ],
  "Kraum, Ludevic's Opus / Radiant, Serra Archangel": [
    "Kraum, Ludevic's Opus",
    "Radiant, Serra Archangel"
  ],
  "Kraum, Ludevic's Opus / Ravos, Soultender": [
    "Kraum, Ludevic's Opus",
    "Ravos, Soultender"
  ],
  "Kraum, Ludevic's Opus / Rebbec, Architect of Ascension": [
    "Kraum, Ludevic's Opus",
    "Rebbec, Architect of Ascension"
  ],
  "Kraum, Ludevic's Opus / Reyhan, Last of the Abzan": [
    "Kraum, Ludevic's Opus",
    "Reyhan, Last of the Abzan"
  ],
  "Kraum, Ludevic's Opus / Rograkh, Son of Rohgahh": [
    "Kraum, Ludevic's Opus",
    "Rograkh, Son of Rohgahh"
  ],
  "Kraum, Ludevic's Opus / Sakashima of a Thousand Faces": [
    "Kraum, Ludevic's Opus",
    "Sakashima of a Thousand Faces"
  ],
  "Kraum, Ludevic's Opus / Sengir, the Dark Baron": [
    "Kraum, Ludevic's Opus",
    "Sengir, the Dark Baron"
  ],
  "Kraum, Ludevic's Opus / Siani, Eye of the Storm": [
    "Kraum, Ludevic's Opus",
    "Siani, Eye of the Storm"
  ],
  "Kraum, Ludevic's Opus / Sidar Kondo of Jamuraa": [
    "Kraum, Ludevic's Opus",
    "Sidar Kondo of Jamuraa"
  ],
  "Kraum, Ludevic's Opus / Silas Renn, Seeker Adept": [
    "Kraum, Ludevic's Opus",
    "Silas Renn, Seeker Adept"
  ],
  "Kraum, Ludevic's Opus / Slurrk, All-Ingesting": [
    "Kraum, Ludevic's Opus",
    "Slurrk, All-Ingesting"
  ],
  "Kraum, Ludevic's Opus / Tana, the Bloodsower": [
    "Kraum, Ludevic's Opus",
    "Tana, the Bloodsower"
  ],
  "Kraum, Ludevic's Opus / Tevesh Szat, Doom of Fools": [
    "Tevesh Szat, Doom of Fools",
    "Kraum, Ludevic's Opus"
  ],
  "Kraum, Ludevic's Opus / The Prismatic Piper": [
    "Kraum, Ludevic's Opus",
    "The Prismatic Piper"
  ],
  "Kraum, Ludevic's Opus / Thrasios, Triton Hero": [
    "Kraum, Ludevic's Opus",
    "Thrasios, Triton Hero"
  ],
  "Kraum, Ludevic's Opus / Toggo, Goblin Weaponsmith": [
    "Kraum, Ludevic's Opus",
    "Toggo, Goblin Weaponsmith"
  ],
  "Kraum, Ludevic's Opus / Tormod, the Desecrator": [
    "Kraum, Ludevic's Opus",
    "Tormod, the Desecrator"
  ],
  "Kraum, Ludevic's Opus / Tymna the Weaver": [
    "Tymna the Weaver",
    "Kraum, Ludevic's Opus"
  ],
  "Kraum, Ludevic's Opus / Vial Smasher the Fierce": [
    "Kraum, Ludevic's Opus",
    "Vial Smasher the Fierce"
  ],
  "Kraum, Ludevic's Opus / Yoshimaru, Ever Faithful": [
    "Kraum, Ludevic's Opus",
    "Yoshimaru, Ever Faithful"
  ],
  "Krav, the Unredeemed / Regna, the Redeemer": [
    "Krav, the Unredeemed",
    "Regna, the Redeemer"
  ],
  "Kydele, Chosen of Kruphix / Livio, Oathsworn Sentinel": [
    "Kydele, Chosen of Kruphix",
    "Livio, Oathsworn Sentinel"
  ],
  "Kydele, Chosen of Kruphix / Ludevic, Necro-Alchemist": [
    "Kydele, Chosen of Kruphix",
    "Ludevic, Necro-Alchemist"
  ],
  "Kydele, Chosen of Kruphix / Malcolm, Keen-Eyed Navigator": [
    "Kydele, Chosen of Kruphix",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Kydele, Chosen of Kruphix / Miara, Thorn of the Glade": [
    "Kydele, Chosen of Kruphix",
    "Miara, Thorn of the Glade"
  ],
  "Kydele, Chosen of Kruphix / Nadier, Agent of the Duskenel": [
    "Kydele, Chosen of Kruphix",
    "Nadier, Agent of the Duskenel"
  ],
  "Kydele, Chosen of Kruphix / Numa, Joraga Chieftain": [
    "Kydele, Chosen of Kruphix",
    "Numa, Joraga Chieftain"
  ],
  "Kydele, Chosen of Kruphix / Prava of the Steel Legion": [
    "Kydele, Chosen of Kruphix",
    "Prava of the Steel Legion"
  ],
  "Kydele, Chosen of Kruphix / Radiant, Serra Archangel": [
    "Kydele, Chosen of Kruphix",
    "Radiant, Serra Archangel"
  ],
  "Kydele, Chosen of Kruphix / Ravos, Soultender": [
    "Kydele, Chosen of Kruphix",
    "Ravos, Soultender"
  ],
  "Kydele, Chosen of Kruphix / Rebbec, Architect of Ascension": [
    "Kydele, Chosen of Kruphix",
    "Rebbec, Architect of Ascension"
  ],
  "Kydele, Chosen of Kruphix / Reyhan, Last of the Abzan": [
    "Kydele, Chosen of Kruphix",
    "Reyhan, Last of the Abzan"
  ],
  "Kydele, Chosen of Kruphix / Rograkh, Son of Rohgahh": [
    "Kydele, Chosen of Kruphix",
    "Rograkh, Son of Rohgahh"
  ],
  "Kydele, Chosen of Kruphix / Sakashima of a Thousand Faces": [
    "Kydele, Chosen of Kruphix",
    "Sakashima of a Thousand Faces"
  ],
  "Kydele, Chosen of Kruphix / Sengir, the Dark Baron": [
    "Kydele, Chosen of Kruphix",
    "Sengir, the Dark Baron"
  ],
  "Kydele, Chosen of Kruphix / Siani, Eye of the Storm": [
    "Kydele, Chosen of Kruphix",
    "Siani, Eye of the Storm"
  ],
  "Kydele, Chosen of Kruphix / Sidar Kondo of Jamuraa": [
    "Kydele, Chosen of Kruphix",
    "Sidar Kondo of Jamuraa"
  ],
  "Kydele, Chosen of Kruphix / Silas Renn, Seeker Adept": [
    "Kydele, Chosen of Kruphix",
    "Silas Renn, Seeker Adept"
  ],
  "Kydele, Chosen of Kruphix / Slurrk, All-Ingesting": [
    "Kydele, Chosen of Kruphix",
    "Slurrk, All-Ingesting"
  ],
  "Kydele, Chosen of Kruphix / Tana, the Bloodsower": [
    "Kydele, Chosen of Kruphix",
    "Tana, the Bloodsower"
  ],
  "Kydele, Chosen of Kruphix / Tevesh Szat, Doom of Fools": [
    "Kydele, Chosen of Kruphix",
    "Tevesh Szat, Doom of Fools"
  ],
  "Kydele, Chosen of Kruphix / The Prismatic Piper": [
    "Kydele, Chosen of Kruphix",
    "The Prismatic Piper"
  ],
  "Kydele, Chosen of Kruphix / Thrasios, Triton Hero": [
    "Kydele, Chosen of Kruphix",
    "Thrasios, Triton Hero"
  ],
  "Kydele, Chosen of Kruphix / Toggo, Goblin Weaponsmith": [
    "Kydele, Chosen of Kruphix",
    "Toggo, Goblin Weaponsmith"
  ],
  "Kydele, Chosen of Kruphix / Tormod, the Desecrator": [
    "Kydele, Chosen of Kruphix",
    "Tormod, the Desecrator"
  ],
  "Kydele, Chosen of Kruphix / Tymna the Weaver": [
    "Kydele, Chosen of Kruphix",
    "Tymna the Weaver"
  ],
  "Kydele, Chosen of Kruphix / Vial Smasher the Fierce": [
    "Kydele, Chosen of Kruphix",
    "Vial Smasher the Fierce"
  ],
  "Kydele, Chosen of Kruphix / Yoshimaru, Ever Faithful": [
    "Kydele, Chosen of Kruphix",
    "Yoshimaru, Ever Faithful"
  ],
  "Lae'zel, Vlaakith's Champion / Master Chef": [
    "Lae'zel, Vlaakith's Champion",
    "Master Chef"
  ],
  "Lae'zel, Vlaakith's Champion / Noble Heritage": [
    "Lae'zel, Vlaakith's Champion",
    "Noble Heritage"
  ],
  "Lae'zel, Vlaakith's Champion / Passionate Archaeologist": [
    "Lae'zel, Vlaakith's Champion",
    "Passionate Archaeologist"
  ],
  "Lae'zel, Vlaakith's Champion / Popular Entertainer": [
    "Lae'zel, Vlaakith's Champion",
    "Popular Entertainer"
  ],
  "Lae'zel, Vlaakith's Champion / Raised by Giants": [
    "Lae'zel, Vlaakith's Champion",
    "Raised by Giants"
  ],
  "Lae'zel, Vlaakith's Champion / Scion of Halaster": [
    "Lae'zel, Vlaakith's Champion",
    "Scion of Halaster"
  ],
  "Lae'zel, Vlaakith's Champion / Shameless Charlatan": [
    "Lae'zel, Vlaakith's Champion",
    "Shameless Charlatan"
  ],
  "Lae'zel, Vlaakith's Champion / Street Urchin": [
    "Lae'zel, Vlaakith's Champion",
    "Street Urchin"
  ],
  "Lae'zel, Vlaakith's Champion / Sword Coast Sailor": [
    "Lae'zel, Vlaakith's Champion",
    "Sword Coast Sailor"
  ],
  "Lae'zel, Vlaakith's Champion / Tavern Brawler": [
    "Lae'zel, Vlaakith's Champion",
    "Tavern Brawler"
  ],
  "Lae'zel, Vlaakith's Champion / Veteran Soldier": [
    "Lae'zel, Vlaakith's Champion",
    "Veteran Soldier"
  ],
  "Leela, Sevateem Warrior / The Eighth Doctor": [
    "Leela, Sevateem Warrior",
    "The Eighth Doctor"
  ],
  "Leela, Sevateem Warrior / The Eleventh Doctor": [
    "Leela, Sevateem Warrior",
    "The Eleventh Doctor"
  ],
  "Leela, Sevateem Warrior / The Fifteenth Doctor": [
    "Leela, Sevateem Warrior",
    "The Fifteenth Doctor"
  ],
  "Leela, Sevateem Warrior / The Fifth Doctor": [
    "Leela, Sevateem Warrior",
    "The Fifth Doctor"
  ],
  "Leela, Sevateem Warrior / The First Doctor": [
    "Leela, Sevateem Warrior",
    "The First Doctor"
  ],
  "Leela, Sevateem Warrior / The Fourteenth Doctor": [
    "Leela, Sevateem Warrior",
    "The Fourteenth Doctor"
  ],
  "Leela, Sevateem Warrior / The Fourth Doctor": [
    "Leela, Sevateem Warrior",
    "The Fourth Doctor"
  ],
  "Leela, Sevateem Warrior / The Fugitive Doctor": [
    "Leela, Sevateem Warrior",
    "The Fugitive Doctor"
  ],
  "Leela, Sevateem Warrior / The Ninth Doctor": [
    "Leela, Sevateem Warrior",
    "The Ninth Doctor"
  ],
  "Leela, Sevateem Warrior / The Second Doctor": [
    "Leela, Sevateem Warrior",
    "The Second Doctor"
  ],
  "Leela, Sevateem Warrior / The Seventh Doctor": [
    "Leela, Sevateem Warrior",
    "The Seventh Doctor"
  ],
  "Leela, Sevateem Warrior / The Sixth Doctor": [
    "Leela, Sevateem Warrior",
    "The Sixth Doctor"
  ],
  "Leela, Sevateem Warrior / The Tenth Doctor": [
    "Leela, Sevateem Warrior",
    "The Tenth Doctor"
  ],
  "Leela, Sevateem Warrior / The Third Doctor": [
    "Leela, Sevateem Warrior",
    "The Third Doctor"
  ],
  "Leela, Sevateem Warrior / The Thirteenth Doctor": [
    "Leela, Sevateem Warrior",
    "The Thirteenth Doctor"
  ],
  "Leela, Sevateem Warrior / The Twelfth Doctor": [
    "Leela, Sevateem Warrior",
    "The Twelfth Doctor"
  ],
  "Leela, Sevateem Warrior / The War Doctor": [
    "Leela, Sevateem Warrior",
    "The War Doctor"
  ],
  "Leonardo, the Balance / Michelangelo, the Heart": [
    "Leonardo, the Balance",
    "Michelangelo, the Heart"
  ],
  "Leonardo, the Balance / Raphael, the Muscle": [
    "Leonardo, the Balance",
    "Raphael, the Muscle"
  ],
  "Leonardo, the Balance / Splinter, the Mentor": [
    "Leonardo, the Balance",
    "Splinter, the Mentor"
  ],
  "Livaan, Cultist of Tiamat / Master Chef": [
    "Livaan, Cultist of Tiamat",
    "Master Chef"
  ],
  "Livaan, Cultist of Tiamat / Noble Heritage": [
    "Livaan, Cultist of Tiamat",
    "Noble Heritage"
  ],
  "Livaan, Cultist of Tiamat / Passionate Archaeologist": [
    "Livaan, Cultist of Tiamat",
    "Passionate Archaeologist"
  ],
  "Livaan, Cultist of Tiamat / Popular Entertainer": [
    "Livaan, Cultist of Tiamat",
    "Popular Entertainer"
  ],
  "Livaan, Cultist of Tiamat / Raised by Giants": [
    "Livaan, Cultist of Tiamat",
    "Raised by Giants"
  ],
  "Livaan, Cultist of Tiamat / Scion of Halaster": [
    "Livaan, Cultist of Tiamat",
    "Scion of Halaster"
  ],
  "Livaan, Cultist of Tiamat / Shameless Charlatan": [
    "Livaan, Cultist of Tiamat",
    "Shameless Charlatan"
  ],
  "Livaan, Cultist of Tiamat / Street Urchin": [
    "Livaan, Cultist of Tiamat",
    "Street Urchin"
  ],
  "Livaan, Cultist of Tiamat / Sword Coast Sailor": [
    "Livaan, Cultist of Tiamat",
    "Sword Coast Sailor"
  ],
  "Livaan, Cultist of Tiamat / Tavern Brawler": [
    "Livaan, Cultist of Tiamat",
    "Tavern Brawler"
  ],
  "Livaan, Cultist of Tiamat / Veteran Soldier": [
    "Livaan, Cultist of Tiamat",
    "Veteran Soldier"
  ],
  "Livio, Oathsworn Sentinel / Ludevic, Necro-Alchemist": [
    "Livio, Oathsworn Sentinel",
    "Ludevic, Necro-Alchemist"
  ],
  "Livio, Oathsworn Sentinel / Malcolm, Keen-Eyed Navigator": [
    "Livio, Oathsworn Sentinel",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Livio, Oathsworn Sentinel / Miara, Thorn of the Glade": [
    "Livio, Oathsworn Sentinel",
    "Miara, Thorn of the Glade"
  ],
  "Livio, Oathsworn Sentinel / Nadier, Agent of the Duskenel": [
    "Livio, Oathsworn Sentinel",
    "Nadier, Agent of the Duskenel"
  ],
  "Livio, Oathsworn Sentinel / Numa, Joraga Chieftain": [
    "Livio, Oathsworn Sentinel",
    "Numa, Joraga Chieftain"
  ],
  "Livio, Oathsworn Sentinel / Prava of the Steel Legion": [
    "Livio, Oathsworn Sentinel",
    "Prava of the Steel Legion"
  ],
  "Livio, Oathsworn Sentinel / Radiant, Serra Archangel": [
    "Livio, Oathsworn Sentinel",
    "Radiant, Serra Archangel"
  ],
  "Livio, Oathsworn Sentinel / Ravos, Soultender": [
    "Livio, Oathsworn Sentinel",
    "Ravos, Soultender"
  ],
  "Livio, Oathsworn Sentinel / Rebbec, Architect of Ascension": [
    "Livio, Oathsworn Sentinel",
    "Rebbec, Architect of Ascension"
  ],
  "Livio, Oathsworn Sentinel / Reyhan, Last of the Abzan": [
    "Livio, Oathsworn Sentinel",
    "Reyhan, Last of the Abzan"
  ],
  "Livio, Oathsworn Sentinel / Rograkh, Son of Rohgahh": [
    "Livio, Oathsworn Sentinel",
    "Rograkh, Son of Rohgahh"
  ],
  "Livio, Oathsworn Sentinel / Sakashima of a Thousand Faces": [
    "Livio, Oathsworn Sentinel",
    "Sakashima of a Thousand Faces"
  ],
  "Livio, Oathsworn Sentinel / Sengir, the Dark Baron": [
    "Livio, Oathsworn Sentinel",
    "Sengir, the Dark Baron"
  ],
  "Livio, Oathsworn Sentinel / Siani, Eye of the Storm": [
    "Livio, Oathsworn Sentinel",
    "Siani, Eye of the Storm"
  ],
  "Livio, Oathsworn Sentinel / Sidar Kondo of Jamuraa": [
    "Livio, Oathsworn Sentinel",
    "Sidar Kondo of Jamuraa"
  ],
  "Livio, Oathsworn Sentinel / Silas Renn, Seeker Adept": [
    "Livio, Oathsworn Sentinel",
    "Silas Renn, Seeker Adept"
  ],
  "Livio, Oathsworn Sentinel / Slurrk, All-Ingesting": [
    "Livio, Oathsworn Sentinel",
    "Slurrk, All-Ingesting"
  ],
  "Livio, Oathsworn Sentinel / Tana, the Bloodsower": [
    "Livio, Oathsworn Sentinel",
    "Tana, the Bloodsower"
  ],
  "Livio, Oathsworn Sentinel / Tevesh Szat, Doom of Fools": [
    "Livio, Oathsworn Sentinel",
    "Tevesh Szat, Doom of Fools"
  ],
  "Livio, Oathsworn Sentinel / The Prismatic Piper": [
    "Livio, Oathsworn Sentinel",
    "The Prismatic Piper"
  ],
  "Livio, Oathsworn Sentinel / Thrasios, Triton Hero": [
    "Livio, Oathsworn Sentinel",
    "Thrasios, Triton Hero"
  ],
  "Livio, Oathsworn Sentinel / Toggo, Goblin Weaponsmith": [
    "Livio, Oathsworn Sentinel",
    "Toggo, Goblin Weaponsmith"
  ],
  "Livio, Oathsworn Sentinel / Tormod, the Desecrator": [
    "Livio, Oathsworn Sentinel",
    "Tormod, the Desecrator"
  ],
  "Livio, Oathsworn Sentinel / Tymna the Weaver": [
    "Livio, Oathsworn Sentinel",
    "Tymna the Weaver"
  ],
  "Livio, Oathsworn Sentinel / Vial Smasher the Fierce": [
    "Livio, Oathsworn Sentinel",
    "Vial Smasher the Fierce"
  ],
  "Livio, Oathsworn Sentinel / Yoshimaru, Ever Faithful": [
    "Livio, Oathsworn Sentinel",
    "Yoshimaru, Ever Faithful"
  ],
  "Ludevic, Necro-Alchemist / Malcolm, Keen-Eyed Navigator": [
    "Ludevic, Necro-Alchemist",
    "Malcolm, Keen-Eyed Navigator"
  ],
  "Ludevic, Necro-Alchemist / Miara, Thorn of the Glade": [
    "Ludevic, Necro-Alchemist",
    "Miara, Thorn of the Glade"
  ],
  "Ludevic, Necro-Alchemist / Nadier, Agent of the Duskenel": [
    "Ludevic, Necro-Alchemist",
    "Nadier, Agent of the Duskenel"
  ],
  "Ludevic, Necro-Alchemist / Numa, Joraga Chieftain": [
    "Ludevic, Necro-Alchemist",
    "Numa, Joraga Chieftain"
  ],
  "Ludevic, Necro-Alchemist / Prava of the Steel Legion": [
    "Ludevic, Necro-Alchemist",
    "Prava of the Steel Legion"
  ],
  "Ludevic, Necro-Alchemist / Radiant, Serra Archangel": [
    "Ludevic, Necro-Alchemist",
    "Radiant, Serra Archangel"
  ],
  "Ludevic, Necro-Alchemist / Ravos, Soultender": [
    "Ludevic, Necro-Alchemist",
    "Ravos, Soultender"
  ],
  "Ludevic, Necro-Alchemist / Rebbec, Architect of Ascension": [
    "Ludevic, Necro-Alchemist",
    "Rebbec, Architect of Ascension"
  ],
  "Ludevic, Necro-Alchemist / Reyhan, Last of the Abzan": [
    "Ludevic, Necro-Alchemist",
    "Reyhan, Last of the Abzan"
  ],
  "Ludevic, Necro-Alchemist / Rograkh, Son of Rohgahh": [
    "Ludevic, Necro-Alchemist",
    "Rograkh, Son of Rohgahh"
  ],
  "Ludevic, Necro-Alchemist / Sakashima of a Thousand Faces": [
    "Ludevic, Necro-Alchemist",
    "Sakashima of a Thousand Faces"
  ],
  "Ludevic, Necro-Alchemist / Sengir, the Dark Baron": [
    "Ludevic, Necro-Alchemist",
    "Sengir, the Dark Baron"
  ],
  "Ludevic, Necro-Alchemist / Siani, Eye of the Storm": [
    "Ludevic, Necro-Alchemist",
    "Siani, Eye of the Storm"
  ],
  "Ludevic, Necro-Alchemist / Sidar Kondo of Jamuraa": [
    "Ludevic, Necro-Alchemist",
    "Sidar Kondo of Jamuraa"
  ],
  "Ludevic, Necro-Alchemist / Silas Renn, Seeker Adept": [
    "Ludevic, Necro-Alchemist",
    "Silas Renn, Seeker Adept"
  ],
  "Ludevic, Necro-Alchemist / Slurrk, All-Ingesting": [
    "Ludevic, Necro-Alchemist",
    "Slurrk, All-Ingesting"
  ],
  "Ludevic, Necro-Alchemist / Tana, the Bloodsower": [
    "Ludevic, Necro-Alchemist",
    "Tana, the Bloodsower"
  ],
  "Ludevic, Necro-Alchemist / Tevesh Szat, Doom of Fools": [
    "Ludevic, Necro-Alchemist",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ludevic, Necro-Alchemist / The Prismatic Piper": [
    "Ludevic, Necro-Alchemist",
    "The Prismatic Piper"
  ],
  "Ludevic, Necro-Alchemist / Thrasios, Triton Hero": [
    "Ludevic, Necro-Alchemist",
    "Thrasios, Triton Hero"
  ],
  "Ludevic, Necro-Alchemist / Toggo, Goblin Weaponsmith": [
    "Ludevic, Necro-Alchemist",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ludevic, Necro-Alchemist / Tormod, the Desecrator": [
    "Ludevic, Necro-Alchemist",
    "Tormod, the Desecrator"
  ],
  "Ludevic, Necro-Alchemist / Tymna the Weaver": [
    "Ludevic, Necro-Alchemist",
    "Tymna the Weaver"
  ],
  "Ludevic, Necro-Alchemist / Vial Smasher the Fierce": [
    "Ludevic, Necro-Alchemist",
    "Vial Smasher the Fierce"
  ],
  "Ludevic, Necro-Alchemist / Yoshimaru, Ever Faithful": [
    "Ludevic, Necro-Alchemist",
    "Yoshimaru, Ever Faithful"
  ],
  "Lulu, Loyal Hollyphant / Master Chef": [
    "Lulu, Loyal Hollyphant",
    "Master Chef"
  ],
  "Lulu, Loyal Hollyphant / Noble Heritage": [
    "Lulu, Loyal Hollyphant",
    "Noble Heritage"
  ],
  "Lulu, Loyal Hollyphant / Passionate Archaeologist": [
    "Lulu, Loyal Hollyphant",
    "Passionate Archaeologist"
  ],
  "Lulu, Loyal Hollyphant / Popular Entertainer": [
    "Lulu, Loyal Hollyphant",
    "Popular Entertainer"
  ],
  "Lulu, Loyal Hollyphant / Raised by Giants": [
    "Lulu, Loyal Hollyphant",
    "Raised by Giants"
  ],
  "Lulu, Loyal Hollyphant / Scion of Halaster": [
    "Lulu, Loyal Hollyphant",
    "Scion of Halaster"
  ],
  "Lulu, Loyal Hollyphant / Shameless Charlatan": [
    "Lulu, Loyal Hollyphant",
    "Shameless Charlatan"
  ],
  "Lulu, Loyal Hollyphant / Street Urchin": [
    "Lulu, Loyal Hollyphant",
    "Street Urchin"
  ],
  "Lulu, Loyal Hollyphant / Sword Coast Sailor": [
    "Lulu, Loyal Hollyphant",
    "Sword Coast Sailor"
  ],
  "Lulu, Loyal Hollyphant / Tavern Brawler": [
    "Lulu, Loyal Hollyphant",
    "Tavern Brawler"
  ],
  "Lulu, Loyal Hollyphant / Veteran Soldier": [
    "Lulu, Loyal Hollyphant",
    "Veteran Soldier"
  ],
  "Malcolm, Keen-Eyed Navigator / Miara, Thorn of the Glade": [
    "Malcolm, Keen-Eyed Navigator",
    "Miara, Thorn of the Glade"
  ],
  "Malcolm, Keen-Eyed Navigator / Nadier, Agent of the Duskenel": [
    "Malcolm, Keen-Eyed Navigator",
    "Nadier, Agent of the Duskenel"
  ],
  "Malcolm, Keen-Eyed Navigator / Numa, Joraga Chieftain": [
    "Malcolm, Keen-Eyed Navigator",
    "Numa, Joraga Chieftain"
  ],
  "Malcolm, Keen-Eyed Navigator / Prava of the Steel Legion": [
    "Malcolm, Keen-Eyed Navigator",
    "Prava of the Steel Legion"
  ],
  "Malcolm, Keen-Eyed Navigator / Radiant, Serra Archangel": [
    "Malcolm, Keen-Eyed Navigator",
    "Radiant, Serra Archangel"
  ],
  "Malcolm, Keen-Eyed Navigator / Ravos, Soultender": [
    "Malcolm, Keen-Eyed Navigator",
    "Ravos, Soultender"
  ],
  "Malcolm, Keen-Eyed Navigator / Rebbec, Architect of Ascension": [
    "Malcolm, Keen-Eyed Navigator",
    "Rebbec, Architect of Ascension"
  ],
  "Malcolm, Keen-Eyed Navigator / Reyhan, Last of the Abzan": [
    "Malcolm, Keen-Eyed Navigator",
    "Reyhan, Last of the Abzan"
  ],
  "Malcolm, Keen-Eyed Navigator / Rograkh, Son of Rohgahh": [
    "Malcolm, Keen-Eyed Navigator",
    "Rograkh, Son of Rohgahh"
  ],
  "Malcolm, Keen-Eyed Navigator / Sakashima of a Thousand Faces": [
    "Malcolm, Keen-Eyed Navigator",
    "Sakashima of a Thousand Faces"
  ],
  "Malcolm, Keen-Eyed Navigator / Sengir, the Dark Baron": [
    "Malcolm, Keen-Eyed Navigator",
    "Sengir, the Dark Baron"
  ],
  "Malcolm, Keen-Eyed Navigator / Siani, Eye of the Storm": [
    "Malcolm, Keen-Eyed Navigator",
    "Siani, Eye of the Storm"
  ],
  "Malcolm, Keen-Eyed Navigator / Sidar Kondo of Jamuraa": [
    "Malcolm, Keen-Eyed Navigator",
    "Sidar Kondo of Jamuraa"
  ],
  "Malcolm, Keen-Eyed Navigator / Silas Renn, Seeker Adept": [
    "Malcolm, Keen-Eyed Navigator",
    "Silas Renn, Seeker Adept"
  ],
  "Malcolm, Keen-Eyed Navigator / Slurrk, All-Ingesting": [
    "Malcolm, Keen-Eyed Navigator",
    "Slurrk, All-Ingesting"
  ],
  "Malcolm, Keen-Eyed Navigator / Tana, the Bloodsower": [
    "Malcolm, Keen-Eyed Navigator",
    "Tana, the Bloodsower"
  ],
  "Malcolm, Keen-Eyed Navigator / Tevesh Szat, Doom of Fools": [
    "Malcolm, Keen-Eyed Navigator",
    "Tevesh Szat, Doom of Fools"
  ],
  "Malcolm, Keen-Eyed Navigator / The Prismatic Piper": [
    "Malcolm, Keen-Eyed Navigator",
    "The Prismatic Piper"
  ],
  "Malcolm, Keen-Eyed Navigator / Thrasios, Triton Hero": [
    "Malcolm, Keen-Eyed Navigator",
    "Thrasios, Triton Hero"
  ],
  "Malcolm, Keen-Eyed Navigator / Toggo, Goblin Weaponsmith": [
    "Malcolm, Keen-Eyed Navigator",
    "Toggo, Goblin Weaponsmith"
  ],
  "Malcolm, Keen-Eyed Navigator / Tormod, the Desecrator": [
    "Malcolm, Keen-Eyed Navigator",
    "Tormod, the Desecrator"
  ],
  "Malcolm, Keen-Eyed Navigator / Tymna the Weaver": [
    "Malcolm, Keen-Eyed Navigator",
    "Tymna the Weaver"
  ],
  "Malcolm, Keen-Eyed Navigator / Vial Smasher the Fierce": [
    "Malcolm, Keen-Eyed Navigator",
    "Vial Smasher the Fierce"
  ],
  "Malcolm, Keen-Eyed Navigator / Yoshimaru, Ever Faithful": [
    "Malcolm, Keen-Eyed Navigator",
    "Yoshimaru, Ever Faithful"
  ],
  "Martha Jones / The Eighth Doctor": [
    "Martha Jones",
    "The Eighth Doctor"
  ],
  "Martha Jones / The Eleventh Doctor": [
    "Martha Jones",
    "The Eleventh Doctor"
  ],
  "Martha Jones / The Fifteenth Doctor": [
    "Martha Jones",
    "The Fifteenth Doctor"
  ],
  "Martha Jones / The Fifth Doctor": [
    "Martha Jones",
    "The Fifth Doctor"
  ],
  "Martha Jones / The First Doctor": [
    "Martha Jones",
    "The First Doctor"
  ],
  "Martha Jones / The Fourteenth Doctor": [
    "Martha Jones",
    "The Fourteenth Doctor"
  ],
  "Martha Jones / The Fourth Doctor": [
    "Martha Jones",
    "The Fourth Doctor"
  ],
  "Martha Jones / The Fugitive Doctor": [
    "Martha Jones",
    "The Fugitive Doctor"
  ],
  "Martha Jones / The Ninth Doctor": [
    "Martha Jones",
    "The Ninth Doctor"
  ],
  "Martha Jones / The Second Doctor": [
    "Martha Jones",
    "The Second Doctor"
  ],
  "Martha Jones / The Seventh Doctor": [
    "Martha Jones",
    "The Seventh Doctor"
  ],
  "Martha Jones / The Sixth Doctor": [
    "Martha Jones",
    "The Sixth Doctor"
  ],
  "Martha Jones / The Tenth Doctor": [
    "Martha Jones",
    "The Tenth Doctor"
  ],
  "Martha Jones / The Third Doctor": [
    "Martha Jones",
    "The Third Doctor"
  ],
  "Martha Jones / The Thirteenth Doctor": [
    "Martha Jones",
    "The Thirteenth Doctor"
  ],
  "Martha Jones / The Twelfth Doctor": [
    "Martha Jones",
    "The Twelfth Doctor"
  ],
  "Martha Jones / The War Doctor": [
    "Martha Jones",
    "The War Doctor"
  ],
  "Master Chef / Rasaad yn Bashir": [
    "Master Chef",
    "Rasaad yn Bashir"
  ],
  "Master Chef / Renari, Merchant of Marvels": [
    "Master Chef",
    "Renari, Merchant of Marvels"
  ],
  "Master Chef / Safana, Calimport Cutthroat": [
    "Master Chef",
    "Safana, Calimport Cutthroat"
  ],
  "Master Chef / Sarevok, Deathbringer": [
    "Master Chef",
    "Sarevok, Deathbringer"
  ],
  "Master Chef / Shadowheart, Dark Justiciar": [
    "Master Chef",
    "Shadowheart, Dark Justiciar"
  ],
  "Master Chef / Sivriss, Nightmare Speaker": [
    "Master Chef",
    "Sivriss, Nightmare Speaker"
  ],
  "Master Chef / Skanos Dragonheart": [
    "Master Chef",
    "Skanos Dragonheart"
  ],
  "Master Chef / Vhal, Candlekeep Researcher": [
    "Master Chef",
    "Vhal, Candlekeep Researcher"
  ],
  "Master Chef / Viconia, Drow Apostate": [
    "Master Chef",
    "Viconia, Drow Apostate"
  ],
  "Master Chef / Volo, Itinerant Scholar": [
    "Master Chef",
    "Volo, Itinerant Scholar"
  ],
  "Master Chef / Wilson, Refined Grizzly": [
    "Master Chef",
    "Wilson, Refined Grizzly"
  ],
  "Master Chef / Wyll, Blade of Frontiers": [
    "Master Chef",
    "Wyll, Blade of Frontiers"
  ],
  "Master Chef / Zellix, Sanity Flayer": [
    "Master Chef",
    "Zellix, Sanity Flayer"
  ],
  "Merry, Warden of Isengard / Pippin, Warden of Isengard": [
    "Merry, Warden of Isengard",
    "Pippin, Warden of Isengard"
  ],
  "Miara, Thorn of the Glade / Nadier, Agent of the Duskenel": [
    "Miara, Thorn of the Glade",
    "Nadier, Agent of the Duskenel"
  ],
  "Miara, Thorn of the Glade / Numa, Joraga Chieftain": [
    "Miara, Thorn of the Glade",
    "Numa, Joraga Chieftain"
  ],
  "Miara, Thorn of the Glade / Prava of the Steel Legion": [
    "Miara, Thorn of the Glade",
    "Prava of the Steel Legion"
  ],
  "Miara, Thorn of the Glade / Radiant, Serra Archangel": [
    "Miara, Thorn of the Glade",
    "Radiant, Serra Archangel"
  ],
  "Miara, Thorn of the Glade / Ravos, Soultender": [
    "Miara, Thorn of the Glade",
    "Ravos, Soultender"
  ],
  "Miara, Thorn of the Glade / Rebbec, Architect of Ascension": [
    "Miara, Thorn of the Glade",
    "Rebbec, Architect of Ascension"
  ],
  "Miara, Thorn of the Glade / Reyhan, Last of the Abzan": [
    "Miara, Thorn of the Glade",
    "Reyhan, Last of the Abzan"
  ],
  "Miara, Thorn of the Glade / Rograkh, Son of Rohgahh": [
    "Miara, Thorn of the Glade",
    "Rograkh, Son of Rohgahh"
  ],
  "Miara, Thorn of the Glade / Sakashima of a Thousand Faces": [
    "Miara, Thorn of the Glade",
    "Sakashima of a Thousand Faces"
  ],
  "Miara, Thorn of the Glade / Sengir, the Dark Baron": [
    "Miara, Thorn of the Glade",
    "Sengir, the Dark Baron"
  ],
  "Miara, Thorn of the Glade / Siani, Eye of the Storm": [
    "Miara, Thorn of the Glade",
    "Siani, Eye of the Storm"
  ],
  "Miara, Thorn of the Glade / Sidar Kondo of Jamuraa": [
    "Miara, Thorn of the Glade",
    "Sidar Kondo of Jamuraa"
  ],
  "Miara, Thorn of the Glade / Silas Renn, Seeker Adept": [
    "Miara, Thorn of the Glade",
    "Silas Renn, Seeker Adept"
  ],
  "Miara, Thorn of the Glade / Slurrk, All-Ingesting": [
    "Miara, Thorn of the Glade",
    "Slurrk, All-Ingesting"
  ],
  "Miara, Thorn of the Glade / Tana, the Bloodsower": [
    "Miara, Thorn of the Glade",
    "Tana, the Bloodsower"
  ],
  "Miara, Thorn of the Glade / Tevesh Szat, Doom of Fools": [
    "Miara, Thorn of the Glade",
    "Tevesh Szat, Doom of Fools"
  ],
  "Miara, Thorn of the Glade / The Prismatic Piper": [
    "Miara, Thorn of the Glade",
    "The Prismatic Piper"
  ],
  "Miara, Thorn of the Glade / Thrasios, Triton Hero": [
    "Miara, Thorn of the Glade",
    "Thrasios, Triton Hero"
  ],
  "Miara, Thorn of the Glade / Toggo, Goblin Weaponsmith": [
    "Miara, Thorn of the Glade",
    "Toggo, Goblin Weaponsmith"
  ],
  "Miara, Thorn of the Glade / Tormod, the Desecrator": [
    "Miara, Thorn of the Glade",
    "Tormod, the Desecrator"
  ],
  "Miara, Thorn of the Glade / Tymna the Weaver": [
    "Miara, Thorn of the Glade",
    "Tymna the Weaver"
  ],
  "Miara, Thorn of the Glade / Vial Smasher the Fierce": [
    "Miara, Thorn of the Glade",
    "Vial Smasher the Fierce"
  ],
  "Miara, Thorn of the Glade / Yoshimaru, Ever Faithful": [
    "Miara, Thorn of the Glade",
    "Yoshimaru, Ever Faithful"
  ],
  "Michelangelo, the Heart / Raphael, the Muscle": [
    "Michelangelo, the Heart",
    "Raphael, the Muscle"
  ],
  "Michelangelo, the Heart / Splinter, the Mentor": [
    "Michelangelo, the Heart",
    "Splinter, the Mentor"
  ],
  "Nadier, Agent of the Duskenel / Numa, Joraga Chieftain": [
    "Nadier, Agent of the Duskenel",
    "Numa, Joraga Chieftain"
  ],
  "Nadier, Agent of the Duskenel / Prava of the Steel Legion": [
    "Nadier, Agent of the Duskenel",
    "Prava of the Steel Legion"
  ],
  "Nadier, Agent of the Duskenel / Radiant, Serra Archangel": [
    "Nadier, Agent of the Duskenel",
    "Radiant, Serra Archangel"
  ],
  "Nadier, Agent of the Duskenel / Ravos, Soultender": [
    "Nadier, Agent of the Duskenel",
    "Ravos, Soultender"
  ],
  "Nadier, Agent of the Duskenel / Rebbec, Architect of Ascension": [
    "Nadier, Agent of the Duskenel",
    "Rebbec, Architect of Ascension"
  ],
  "Nadier, Agent of the Duskenel / Reyhan, Last of the Abzan": [
    "Nadier, Agent of the Duskenel",
    "Reyhan, Last of the Abzan"
  ],
  "Nadier, Agent of the Duskenel / Rograkh, Son of Rohgahh": [
    "Nadier, Agent of the Duskenel",
    "Rograkh, Son of Rohgahh"
  ],
  "Nadier, Agent of the Duskenel / Sakashima of a Thousand Faces": [
    "Nadier, Agent of the Duskenel",
    "Sakashima of a Thousand Faces"
  ],
  "Nadier, Agent of the Duskenel / Sengir, the Dark Baron": [
    "Nadier, Agent of the Duskenel",
    "Sengir, the Dark Baron"
  ],
  "Nadier, Agent of the Duskenel / Siani, Eye of the Storm": [
    "Nadier, Agent of the Duskenel",
    "Siani, Eye of the Storm"
  ],
  "Nadier, Agent of the Duskenel / Sidar Kondo of Jamuraa": [
    "Nadier, Agent of the Duskenel",
    "Sidar Kondo of Jamuraa"
  ],
  "Nadier, Agent of the Duskenel / Silas Renn, Seeker Adept": [
    "Nadier, Agent of the Duskenel",
    "Silas Renn, Seeker Adept"
  ],
  "Nadier, Agent of the Duskenel / Slurrk, All-Ingesting": [
    "Nadier, Agent of the Duskenel",
    "Slurrk, All-Ingesting"
  ],
  "Nadier, Agent of the Duskenel / Tana, the Bloodsower": [
    "Nadier, Agent of the Duskenel",
    "Tana, the Bloodsower"
  ],
  "Nadier, Agent of the Duskenel / Tevesh Szat, Doom of Fools": [
    "Nadier, Agent of the Duskenel",
    "Tevesh Szat, Doom of Fools"
  ],
  "Nadier, Agent of the Duskenel / The Prismatic Piper": [
    "Nadier, Agent of the Duskenel",
    "The Prismatic Piper"
  ],
  "Nadier, Agent of the Duskenel / Thrasios, Triton Hero": [
    "Nadier, Agent of the Duskenel",
    "Thrasios, Triton Hero"
  ],
  "Nadier, Agent of the Duskenel / Toggo, Goblin Weaponsmith": [
    "Nadier, Agent of the Duskenel",
    "Toggo, Goblin Weaponsmith"
  ],
  "Nadier, Agent of the Duskenel / Tormod, the Desecrator": [
    "Nadier, Agent of the Duskenel",
    "Tormod, the Desecrator"
  ],
  "Nadier, Agent of the Duskenel / Tymna the Weaver": [
    "Nadier, Agent of the Duskenel",
    "Tymna the Weaver"
  ],
  "Nadier, Agent of the Duskenel / Vial Smasher the Fierce": [
    "Nadier, Agent of the Duskenel",
    "Vial Smasher the Fierce"
  ],
  "Nadier, Agent of the Duskenel / Yoshimaru, Ever Faithful": [
    "Nadier, Agent of the Duskenel",
    "Yoshimaru, Ever Faithful"
  ],
  "Nardole, Resourceful Cyborg / The Eighth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Eighth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Eleventh Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Eleventh Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Fifteenth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Fifteenth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Fifth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Fifth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The First Doctor": [
    "Nardole, Resourceful Cyborg",
    "The First Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Fourteenth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Fourteenth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Fourth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Fourth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Fugitive Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Fugitive Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Ninth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Ninth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Second Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Second Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Seventh Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Seventh Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Sixth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Sixth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Tenth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Tenth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Third Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Third Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Thirteenth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Thirteenth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The Twelfth Doctor": [
    "Nardole, Resourceful Cyborg",
    "The Twelfth Doctor"
  ],
  "Nardole, Resourceful Cyborg / The War Doctor": [
    "Nardole, Resourceful Cyborg",
    "The War Doctor"
  ],
  "Nikara, Lair Scavenger / Yannik, Scavenging Sentinel": [
    "Nikara, Lair Scavenger",
    "Yannik, Scavenging Sentinel"
  ],
  "Noble Heritage / Rasaad yn Bashir": [
    "Noble Heritage",
    "Rasaad yn Bashir"
  ],
  "Noble Heritage / Renari, Merchant of Marvels": [
    "Noble Heritage",
    "Renari, Merchant of Marvels"
  ],
  "Noble Heritage / Safana, Calimport Cutthroat": [
    "Noble Heritage",
    "Safana, Calimport Cutthroat"
  ],
  "Noble Heritage / Sarevok, Deathbringer": [
    "Noble Heritage",
    "Sarevok, Deathbringer"
  ],
  "Noble Heritage / Shadowheart, Dark Justiciar": [
    "Noble Heritage",
    "Shadowheart, Dark Justiciar"
  ],
  "Noble Heritage / Sivriss, Nightmare Speaker": [
    "Noble Heritage",
    "Sivriss, Nightmare Speaker"
  ],
  "Noble Heritage / Skanos Dragonheart": [
    "Noble Heritage",
    "Skanos Dragonheart"
  ],
  "Noble Heritage / Vhal, Candlekeep Researcher": [
    "Noble Heritage",
    "Vhal, Candlekeep Researcher"
  ],
  "Noble Heritage / Viconia, Drow Apostate": [
    "Noble Heritage",
    "Viconia, Drow Apostate"
  ],
  "Noble Heritage / Volo, Itinerant Scholar": [
    "Noble Heritage",
    "Volo, Itinerant Scholar"
  ],
  "Noble Heritage / Wilson, Refined Grizzly": [
    "Noble Heritage",
    "Wilson, Refined Grizzly"
  ],
  "Noble Heritage / Wyll, Blade of Frontiers": [
    "Noble Heritage",
    "Wyll, Blade of Frontiers"
  ],
  "Noble Heritage / Zellix, Sanity Flayer": [
    "Noble Heritage",
    "Zellix, Sanity Flayer"
  ],
  "Numa, Joraga Chieftain / Prava of the Steel Legion": [
    "Numa, Joraga Chieftain",
    "Prava of the Steel Legion"
  ],
  "Numa, Joraga Chieftain / Radiant, Serra Archangel": [
    "Numa, Joraga Chieftain",
    "Radiant, Serra Archangel"
  ],
  "Numa, Joraga Chieftain / Ravos, Soultender": [
    "Numa, Joraga Chieftain",
    "Ravos, Soultender"
  ],
  "Numa, Joraga Chieftain / Rebbec, Architect of Ascension": [
    "Numa, Joraga Chieftain",
    "Rebbec, Architect of Ascension"
  ],
  "Numa, Joraga Chieftain / Reyhan, Last of the Abzan": [
    "Numa, Joraga Chieftain",
    "Reyhan, Last of the Abzan"
  ],
  "Numa, Joraga Chieftain / Rograkh, Son of Rohgahh": [
    "Numa, Joraga Chieftain",
    "Rograkh, Son of Rohgahh"
  ],
  "Numa, Joraga Chieftain / Sakashima of a Thousand Faces": [
    "Numa, Joraga Chieftain",
    "Sakashima of a Thousand Faces"
  ],
  "Numa, Joraga Chieftain / Sengir, the Dark Baron": [
    "Numa, Joraga Chieftain",
    "Sengir, the Dark Baron"
  ],
  "Numa, Joraga Chieftain / Siani, Eye of the Storm": [
    "Numa, Joraga Chieftain",
    "Siani, Eye of the Storm"
  ],
  "Numa, Joraga Chieftain / Sidar Kondo of Jamuraa": [
    "Numa, Joraga Chieftain",
    "Sidar Kondo of Jamuraa"
  ],
  "Numa, Joraga Chieftain / Silas Renn, Seeker Adept": [
    "Numa, Joraga Chieftain",
    "Silas Renn, Seeker Adept"
  ],
  "Numa, Joraga Chieftain / Slurrk, All-Ingesting": [
    "Numa, Joraga Chieftain",
    "Slurrk, All-Ingesting"
  ],
  "Numa, Joraga Chieftain / Tana, the Bloodsower": [
    "Numa, Joraga Chieftain",
    "Tana, the Bloodsower"
  ],
  "Numa, Joraga Chieftain / Tevesh Szat, Doom of Fools": [
    "Numa, Joraga Chieftain",
    "Tevesh Szat, Doom of Fools"
  ],
  "Numa, Joraga Chieftain / The Prismatic Piper": [
    "Numa, Joraga Chieftain",
    "The Prismatic Piper"
  ],
  "Numa, Joraga Chieftain / Thrasios, Triton Hero": [
    "Numa, Joraga Chieftain",
    "Thrasios, Triton Hero"
  ],
  "Numa, Joraga Chieftain / Toggo, Goblin Weaponsmith": [
    "Numa, Joraga Chieftain",
    "Toggo, Goblin Weaponsmith"
  ],
  "Numa, Joraga Chieftain / Tormod, the Desecrator": [
    "Numa, Joraga Chieftain",
    "Tormod, the Desecrator"
  ],
  "Numa, Joraga Chieftain / Tymna the Weaver": [
    "Numa, Joraga Chieftain",
    "Tymna the Weaver"
  ],
  "Numa, Joraga Chieftain / Vial Smasher the Fierce": [
    "Numa, Joraga Chieftain",
    "Vial Smasher the Fierce"
  ],
  "Numa, Joraga Chieftain / Yoshimaru, Ever Faithful": [
    "Numa, Joraga Chieftain",
    "Yoshimaru, Ever Faithful"
  ],
  "Nyssa of Traken / The Eighth Doctor": [
    "Nyssa of Traken",
    "The Eighth Doctor"
  ],
  "Nyssa of Traken / The Eleventh Doctor": [
    "Nyssa of Traken",
    "The Eleventh Doctor"
  ],
  "Nyssa of Traken / The Fifteenth Doctor": [
    "Nyssa of Traken",
    "The Fifteenth Doctor"
  ],
  "Nyssa of Traken / The Fifth Doctor": [
    "Nyssa of Traken",
    "The Fifth Doctor"
  ],
  "Nyssa of Traken / The First Doctor": [
    "Nyssa of Traken",
    "The First Doctor"
  ],
  "Nyssa of Traken / The Fourteenth Doctor": [
    "Nyssa of Traken",
    "The Fourteenth Doctor"
  ],
  "Nyssa of Traken / The Fourth Doctor": [
    "Nyssa of Traken",
    "The Fourth Doctor"
  ],
  "Nyssa of Traken / The Fugitive Doctor": [
    "Nyssa of Traken",
    "The Fugitive Doctor"
  ],
  "Nyssa of Traken / The Ninth Doctor": [
    "Nyssa of Traken",
    "The Ninth Doctor"
  ],
  "Nyssa of Traken / The Second Doctor": [
    "Nyssa of Traken",
    "The Second Doctor"
  ],
  "Nyssa of Traken / The Seventh Doctor": [
    "Nyssa of Traken",
    "The Seventh Doctor"
  ],
  "Nyssa of Traken / The Sixth Doctor": [
    "Nyssa of Traken",
    "The Sixth Doctor"
  ],
  "Nyssa of Traken / The Tenth Doctor": [
    "Nyssa of Traken",
    "The Tenth Doctor"
  ],
  "Nyssa of Traken / The Third Doctor": [
    "Nyssa of Traken",
    "The Third Doctor"
  ],
  "Nyssa of Traken / The Thirteenth Doctor": [
    "Nyssa of Traken",
    "The Thirteenth Doctor"
  ],
  "Nyssa of Traken / The Twelfth Doctor": [
    "Nyssa of Traken",
    "The Twelfth Doctor"
  ],
  "Nyssa of Traken / The War Doctor": [
    "Nyssa of Traken",
    "The War Doctor"
  ],
  "Okaun, Eye of Chaos / Zndrsplt, Eye of Wisdom": [
    "Okaun, Eye of Chaos",
    "Zndrsplt, Eye of Wisdom"
  ],
  "Othelm, Sigardian Outcast / Sophina, Spearsage Deserter": [
    "Othelm, Sigardian Outcast",
    "Sophina, Spearsage Deserter"
  ],
  "Othelm, Sigardian Outcast / Wernog, Rider's Chaplain": [
    "Othelm, Sigardian Outcast",
    "Wernog, Rider's Chaplain"
  ],
  "Passionate Archaeologist / Rasaad yn Bashir": [
    "Passionate Archaeologist",
    "Rasaad yn Bashir"
  ],
  "Passionate Archaeologist / Renari, Merchant of Marvels": [
    "Passionate Archaeologist",
    "Renari, Merchant of Marvels"
  ],
  "Passionate Archaeologist / Safana, Calimport Cutthroat": [
    "Passionate Archaeologist",
    "Safana, Calimport Cutthroat"
  ],
  "Passionate Archaeologist / Sarevok, Deathbringer": [
    "Passionate Archaeologist",
    "Sarevok, Deathbringer"
  ],
  "Passionate Archaeologist / Shadowheart, Dark Justiciar": [
    "Passionate Archaeologist",
    "Shadowheart, Dark Justiciar"
  ],
  "Passionate Archaeologist / Sivriss, Nightmare Speaker": [
    "Passionate Archaeologist",
    "Sivriss, Nightmare Speaker"
  ],
  "Passionate Archaeologist / Skanos Dragonheart": [
    "Passionate Archaeologist",
    "Skanos Dragonheart"
  ],
  "Passionate Archaeologist / Vhal, Candlekeep Researcher": [
    "Passionate Archaeologist",
    "Vhal, Candlekeep Researcher"
  ],
  "Passionate Archaeologist / Viconia, Drow Apostate": [
    "Passionate Archaeologist",
    "Viconia, Drow Apostate"
  ],
  "Passionate Archaeologist / Volo, Itinerant Scholar": [
    "Passionate Archaeologist",
    "Volo, Itinerant Scholar"
  ],
  "Passionate Archaeologist / Wilson, Refined Grizzly": [
    "Passionate Archaeologist",
    "Wilson, Refined Grizzly"
  ],
  "Passionate Archaeologist / Wyll, Blade of Frontiers": [
    "Passionate Archaeologist",
    "Wyll, Blade of Frontiers"
  ],
  "Passionate Archaeologist / Zellix, Sanity Flayer": [
    "Passionate Archaeologist",
    "Zellix, Sanity Flayer"
  ],
  "Peri Brown / The Eighth Doctor": [
    "Peri Brown",
    "The Eighth Doctor"
  ],
  "Peri Brown / The Eleventh Doctor": [
    "Peri Brown",
    "The Eleventh Doctor"
  ],
  "Peri Brown / The Fifteenth Doctor": [
    "Peri Brown",
    "The Fifteenth Doctor"
  ],
  "Peri Brown / The Fifth Doctor": [
    "Peri Brown",
    "The Fifth Doctor"
  ],
  "Peri Brown / The First Doctor": [
    "Peri Brown",
    "The First Doctor"
  ],
  "Peri Brown / The Fourteenth Doctor": [
    "Peri Brown",
    "The Fourteenth Doctor"
  ],
  "Peri Brown / The Fourth Doctor": [
    "Peri Brown",
    "The Fourth Doctor"
  ],
  "Peri Brown / The Fugitive Doctor": [
    "Peri Brown",
    "The Fugitive Doctor"
  ],
  "Peri Brown / The Ninth Doctor": [
    "Peri Brown",
    "The Ninth Doctor"
  ],
  "Peri Brown / The Second Doctor": [
    "Peri Brown",
    "The Second Doctor"
  ],
  "Peri Brown / The Seventh Doctor": [
    "Peri Brown",
    "The Seventh Doctor"
  ],
  "Peri Brown / The Sixth Doctor": [
    "Peri Brown",
    "The Sixth Doctor"
  ],
  "Peri Brown / The Tenth Doctor": [
    "Peri Brown",
    "The Tenth Doctor"
  ],
  "Peri Brown / The Third Doctor": [
    "Peri Brown",
    "The Third Doctor"
  ],
  "Peri Brown / The Thirteenth Doctor": [
    "Peri Brown",
    "The Thirteenth Doctor"
  ],
  "Peri Brown / The Twelfth Doctor": [
    "Peri Brown",
    "The Twelfth Doctor"
  ],
  "Peri Brown / The War Doctor": [
    "Peri Brown",
    "The War Doctor"
  ],
  "Pir, Imaginative Rascal / Toothy, Imaginary Friend": [
    "Pir, Imaginative Rascal",
    "Toothy, Imaginary Friend"
  ],
  "Popular Entertainer / Rasaad yn Bashir": [
    "Popular Entertainer",
    "Rasaad yn Bashir"
  ],
  "Popular Entertainer / Renari, Merchant of Marvels": [
    "Popular Entertainer",
    "Renari, Merchant of Marvels"
  ],
  "Popular Entertainer / Safana, Calimport Cutthroat": [
    "Popular Entertainer",
    "Safana, Calimport Cutthroat"
  ],
  "Popular Entertainer / Sarevok, Deathbringer": [
    "Popular Entertainer",
    "Sarevok, Deathbringer"
  ],
  "Popular Entertainer / Shadowheart, Dark Justiciar": [
    "Popular Entertainer",
    "Shadowheart, Dark Justiciar"
  ],
  "Popular Entertainer / Sivriss, Nightmare Speaker": [
    "Popular Entertainer",
    "Sivriss, Nightmare Speaker"
  ],
  "Popular Entertainer / Skanos Dragonheart": [
    "Popular Entertainer",
    "Skanos Dragonheart"
  ],
  "Popular Entertainer / Vhal, Candlekeep Researcher": [
    "Popular Entertainer",
    "Vhal, Candlekeep Researcher"
  ],
  "Popular Entertainer / Viconia, Drow Apostate": [
    "Popular Entertainer",
    "Viconia, Drow Apostate"
  ],
  "Popular Entertainer / Volo, Itinerant Scholar": [
    "Popular Entertainer",
    "Volo, Itinerant Scholar"
  ],
  "Popular Entertainer / Wilson, Refined Grizzly": [
    "Popular Entertainer",
    "Wilson, Refined Grizzly"
  ],
  "Popular Entertainer / Wyll, Blade of Frontiers": [
    "Popular Entertainer",
    "Wyll, Blade of Frontiers"
  ],
  "Popular Entertainer / Zellix, Sanity Flayer": [
    "Popular Entertainer",
    "Zellix, Sanity Flayer"
  ],
  "Prava of the Steel Legion / Radiant, Serra Archangel": [
    "Prava of the Steel Legion",
    "Radiant, Serra Archangel"
  ],
  "Prava of the Steel Legion / Ravos, Soultender": [
    "Prava of the Steel Legion",
    "Ravos, Soultender"
  ],
  "Prava of the Steel Legion / Rebbec, Architect of Ascension": [
    "Prava of the Steel Legion",
    "Rebbec, Architect of Ascension"
  ],
  "Prava of the Steel Legion / Reyhan, Last of the Abzan": [
    "Prava of the Steel Legion",
    "Reyhan, Last of the Abzan"
  ],
  "Prava of the Steel Legion / Rograkh, Son of Rohgahh": [
    "Prava of the Steel Legion",
    "Rograkh, Son of Rohgahh"
  ],
  "Prava of the Steel Legion / Sakashima of a Thousand Faces": [
    "Prava of the Steel Legion",
    "Sakashima of a Thousand Faces"
  ],
  "Prava of the Steel Legion / Sengir, the Dark Baron": [
    "Prava of the Steel Legion",
    "Sengir, the Dark Baron"
  ],
  "Prava of the Steel Legion / Siani, Eye of the Storm": [
    "Prava of the Steel Legion",
    "Siani, Eye of the Storm"
  ],
  "Prava of the Steel Legion / Sidar Kondo of Jamuraa": [
    "Prava of the Steel Legion",
    "Sidar Kondo of Jamuraa"
  ],
  "Prava of the Steel Legion / Silas Renn, Seeker Adept": [
    "Prava of the Steel Legion",
    "Silas Renn, Seeker Adept"
  ],
  "Prava of the Steel Legion / Slurrk, All-Ingesting": [
    "Prava of the Steel Legion",
    "Slurrk, All-Ingesting"
  ],
  "Prava of the Steel Legion / Tana, the Bloodsower": [
    "Prava of the Steel Legion",
    "Tana, the Bloodsower"
  ],
  "Prava of the Steel Legion / Tevesh Szat, Doom of Fools": [
    "Prava of the Steel Legion",
    "Tevesh Szat, Doom of Fools"
  ],
  "Prava of the Steel Legion / The Prismatic Piper": [
    "Prava of the Steel Legion",
    "The Prismatic Piper"
  ],
  "Prava of the Steel Legion / Thrasios, Triton Hero": [
    "Prava of the Steel Legion",
    "Thrasios, Triton Hero"
  ],
  "Prava of the Steel Legion / Toggo, Goblin Weaponsmith": [
    "Prava of the Steel Legion",
    "Toggo, Goblin Weaponsmith"
  ],
  "Prava of the Steel Legion / Tormod, the Desecrator": [
    "Prava of the Steel Legion",
    "Tormod, the Desecrator"
  ],
  "Prava of the Steel Legion / Tymna the Weaver": [
    "Prava of the Steel Legion",
    "Tymna the Weaver"
  ],
  "Prava of the Steel Legion / Vial Smasher the Fierce": [
    "Prava of the Steel Legion",
    "Vial Smasher the Fierce"
  ],
  "Prava of the Steel Legion / Yoshimaru, Ever Faithful": [
    "Prava of the Steel Legion",
    "Yoshimaru, Ever Faithful"
  ],
  "Radiant, Serra Archangel / Ravos, Soultender": [
    "Radiant, Serra Archangel",
    "Ravos, Soultender"
  ],
  "Radiant, Serra Archangel / Rebbec, Architect of Ascension": [
    "Radiant, Serra Archangel",
    "Rebbec, Architect of Ascension"
  ],
  "Radiant, Serra Archangel / Reyhan, Last of the Abzan": [
    "Radiant, Serra Archangel",
    "Reyhan, Last of the Abzan"
  ],
  "Radiant, Serra Archangel / Rograkh, Son of Rohgahh": [
    "Radiant, Serra Archangel",
    "Rograkh, Son of Rohgahh"
  ],
  "Radiant, Serra Archangel / Sakashima of a Thousand Faces": [
    "Radiant, Serra Archangel",
    "Sakashima of a Thousand Faces"
  ],
  "Radiant, Serra Archangel / Sengir, the Dark Baron": [
    "Radiant, Serra Archangel",
    "Sengir, the Dark Baron"
  ],
  "Radiant, Serra Archangel / Siani, Eye of the Storm": [
    "Radiant, Serra Archangel",
    "Siani, Eye of the Storm"
  ],
  "Radiant, Serra Archangel / Sidar Kondo of Jamuraa": [
    "Radiant, Serra Archangel",
    "Sidar Kondo of Jamuraa"
  ],
  "Radiant, Serra Archangel / Silas Renn, Seeker Adept": [
    "Radiant, Serra Archangel",
    "Silas Renn, Seeker Adept"
  ],
  "Radiant, Serra Archangel / Slurrk, All-Ingesting": [
    "Radiant, Serra Archangel",
    "Slurrk, All-Ingesting"
  ],
  "Radiant, Serra Archangel / Tana, the Bloodsower": [
    "Radiant, Serra Archangel",
    "Tana, the Bloodsower"
  ],
  "Radiant, Serra Archangel / Tevesh Szat, Doom of Fools": [
    "Radiant, Serra Archangel",
    "Tevesh Szat, Doom of Fools"
  ],
  "Radiant, Serra Archangel / The Prismatic Piper": [
    "Radiant, Serra Archangel",
    "The Prismatic Piper"
  ],
  "Radiant, Serra Archangel / Thrasios, Triton Hero": [
    "Radiant, Serra Archangel",
    "Thrasios, Triton Hero"
  ],
  "Radiant, Serra Archangel / Toggo, Goblin Weaponsmith": [
    "Radiant, Serra Archangel",
    "Toggo, Goblin Weaponsmith"
  ],
  "Radiant, Serra Archangel / Tormod, the Desecrator": [
    "Radiant, Serra Archangel",
    "Tormod, the Desecrator"
  ],
  "Radiant, Serra Archangel / Tymna the Weaver": [
    "Radiant, Serra Archangel",
    "Tymna the Weaver"
  ],
  "Radiant, Serra Archangel / Vial Smasher the Fierce": [
    "Radiant, Serra Archangel",
    "Vial Smasher the Fierce"
  ],
  "Radiant, Serra Archangel / Yoshimaru, Ever Faithful": [
    "Radiant, Serra Archangel",
    "Yoshimaru, Ever Faithful"
  ],
  "Raised by Giants / Rasaad yn Bashir": [
    "Raised by Giants",
    "Rasaad yn Bashir"
  ],
  "Raised by Giants / Renari, Merchant of Marvels": [
    "Raised by Giants",
    "Renari, Merchant of Marvels"
  ],
  "Raised by Giants / Safana, Calimport Cutthroat": [
    "Raised by Giants",
    "Safana, Calimport Cutthroat"
  ],
  "Raised by Giants / Sarevok, Deathbringer": [
    "Raised by Giants",
    "Sarevok, Deathbringer"
  ],
  "Raised by Giants / Shadowheart, Dark Justiciar": [
    "Raised by Giants",
    "Shadowheart, Dark Justiciar"
  ],
  "Raised by Giants / Sivriss, Nightmare Speaker": [
    "Raised by Giants",
    "Sivriss, Nightmare Speaker"
  ],
  "Raised by Giants / Skanos Dragonheart": [
    "Raised by Giants",
    "Skanos Dragonheart"
  ],
  "Raised by Giants / Vhal, Candlekeep Researcher": [
    "Raised by Giants",
    "Vhal, Candlekeep Researcher"
  ],
  "Raised by Giants / Viconia, Drow Apostate": [
    "Raised by Giants",
    "Viconia, Drow Apostate"
  ],
  "Raised by Giants / Volo, Itinerant Scholar": [
    "Raised by Giants",
    "Volo, Itinerant Scholar"
  ],
  "Raised by Giants / Wilson, Refined Grizzly": [
    "Raised by Giants",
    "Wilson, Refined Grizzly"
  ],
  "Raised by Giants / Wyll, Blade of Frontiers": [
    "Raised by Giants",
    "Wyll, Blade of Frontiers"
  ],
  "Raised by Giants / Zellix, Sanity Flayer": [
    "Raised by Giants",
    "Zellix, Sanity Flayer"
  ],
  "Raphael, the Muscle / Splinter, the Mentor": [
    "Raphael, the Muscle",
    "Splinter, the Mentor"
  ],
  "Rasaad yn Bashir / Scion of Halaster": [
    "Rasaad yn Bashir",
    "Scion of Halaster"
  ],
  "Rasaad yn Bashir / Shameless Charlatan": [
    "Rasaad yn Bashir",
    "Shameless Charlatan"
  ],
  "Rasaad yn Bashir / Street Urchin": [
    "Rasaad yn Bashir",
    "Street Urchin"
  ],
  "Rasaad yn Bashir / Sword Coast Sailor": [
    "Rasaad yn Bashir",
    "Sword Coast Sailor"
  ],
  "Rasaad yn Bashir / Tavern Brawler": [
    "Rasaad yn Bashir",
    "Tavern Brawler"
  ],
  "Rasaad yn Bashir / Veteran Soldier": [
    "Rasaad yn Bashir",
    "Veteran Soldier"
  ],
  "Ravos, Soultender / Rebbec, Architect of Ascension": [
    "Ravos, Soultender",
    "Rebbec, Architect of Ascension"
  ],
  "Ravos, Soultender / Reyhan, Last of the Abzan": [
    "Ravos, Soultender",
    "Reyhan, Last of the Abzan"
  ],
  "Ravos, Soultender / Rograkh, Son of Rohgahh": [
    "Ravos, Soultender",
    "Rograkh, Son of Rohgahh"
  ],
  "Ravos, Soultender / Sakashima of a Thousand Faces": [
    "Ravos, Soultender",
    "Sakashima of a Thousand Faces"
  ],
  "Ravos, Soultender / Sengir, the Dark Baron": [
    "Ravos, Soultender",
    "Sengir, the Dark Baron"
  ],
  "Ravos, Soultender / Siani, Eye of the Storm": [
    "Ravos, Soultender",
    "Siani, Eye of the Storm"
  ],
  "Ravos, Soultender / Sidar Kondo of Jamuraa": [
    "Ravos, Soultender",
    "Sidar Kondo of Jamuraa"
  ],
  "Ravos, Soultender / Silas Renn, Seeker Adept": [
    "Ravos, Soultender",
    "Silas Renn, Seeker Adept"
  ],
  "Ravos, Soultender / Slurrk, All-Ingesting": [
    "Ravos, Soultender",
    "Slurrk, All-Ingesting"
  ],
  "Ravos, Soultender / Tana, the Bloodsower": [
    "Ravos, Soultender",
    "Tana, the Bloodsower"
  ],
  "Ravos, Soultender / Tevesh Szat, Doom of Fools": [
    "Ravos, Soultender",
    "Tevesh Szat, Doom of Fools"
  ],
  "Ravos, Soultender / The Prismatic Piper": [
    "Ravos, Soultender",
    "The Prismatic Piper"
  ],
  "Ravos, Soultender / Thrasios, Triton Hero": [
    "Ravos, Soultender",
    "Thrasios, Triton Hero"
  ],
  "Ravos, Soultender / Toggo, Goblin Weaponsmith": [
    "Ravos, Soultender",
    "Toggo, Goblin Weaponsmith"
  ],
  "Ravos, Soultender / Tormod, the Desecrator": [
    "Ravos, Soultender",
    "Tormod, the Desecrator"
  ],
  "Ravos, Soultender / Tymna the Weaver": [
    "Ravos, Soultender",
    "Tymna the Weaver"
  ],
  "Ravos, Soultender / Vial Smasher the Fierce": [
    "Ravos, Soultender",
    "Vial Smasher the Fierce"
  ],
  "Ravos, Soultender / Yoshimaru, Ever Faithful": [
    "Ravos, Soultender",
    "Yoshimaru, Ever Faithful"
  ],
  "Rebbec, Architect of Ascension / Reyhan, Last of the Abzan": [
    "Rebbec, Architect of Ascension",
    "Reyhan, Last of the Abzan"
  ],
  "Rebbec, Architect of Ascension / Rograkh, Son of Rohgahh": [
    "Rebbec, Architect of Ascension",
    "Rograkh, Son of Rohgahh"
  ],
  "Rebbec, Architect of Ascension / Sakashima of a Thousand Faces": [
    "Rebbec, Architect of Ascension",
    "Sakashima of a Thousand Faces"
  ],
  "Rebbec, Architect of Ascension / Sengir, the Dark Baron": [
    "Rebbec, Architect of Ascension",
    "Sengir, the Dark Baron"
  ],
  "Rebbec, Architect of Ascension / Siani, Eye of the Storm": [
    "Rebbec, Architect of Ascension",
    "Siani, Eye of the Storm"
  ],
  "Rebbec, Architect of Ascension / Sidar Kondo of Jamuraa": [
    "Rebbec, Architect of Ascension",
    "Sidar Kondo of Jamuraa"
  ],
  "Rebbec, Architect of Ascension / Silas Renn, Seeker Adept": [
    "Rebbec, Architect of Ascension",
    "Silas Renn, Seeker Adept"
  ],
  "Rebbec, Architect of Ascension / Slurrk, All-Ingesting": [
    "Rebbec, Architect of Ascension",
    "Slurrk, All-Ingesting"
  ],
  "Rebbec, Architect of Ascension / Tana, the Bloodsower": [
    "Rebbec, Architect of Ascension",
    "Tana, the Bloodsower"
  ],
  "Rebbec, Architect of Ascension / Tevesh Szat, Doom of Fools": [
    "Rebbec, Architect of Ascension",
    "Tevesh Szat, Doom of Fools"
  ],
  "Rebbec, Architect of Ascension / The Prismatic Piper": [
    "Rebbec, Architect of Ascension",
    "The Prismatic Piper"
  ],
  "Rebbec, Architect of Ascension / Thrasios, Triton Hero": [
    "Rebbec, Architect of Ascension",
    "Thrasios, Triton Hero"
  ],
  "Rebbec, Architect of Ascension / Toggo, Goblin Weaponsmith": [
    "Rebbec, Architect of Ascension",
    "Toggo, Goblin Weaponsmith"
  ],
  "Rebbec, Architect of Ascension / Tormod, the Desecrator": [
    "Rebbec, Architect of Ascension",
    "Tormod, the Desecrator"
  ],
  "Rebbec, Architect of Ascension / Tymna the Weaver": [
    "Rebbec, Architect of Ascension",
    "Tymna the Weaver"
  ],
  "Rebbec, Architect of Ascension / Vial Smasher the Fierce": [
    "Rebbec, Architect of Ascension",
    "Vial Smasher the Fierce"
  ],
  "Rebbec, Architect of Ascension / Yoshimaru, Ever Faithful": [
    "Rebbec, Architect of Ascension",
    "Yoshimaru, Ever Faithful"
  ],
  "Renari, Merchant of Marvels / Scion of Halaster": [
    "Renari, Merchant of Marvels",
    "Scion of Halaster"
  ],
  "Renari, Merchant of Marvels / Shameless Charlatan": [
    "Renari, Merchant of Marvels",
    "Shameless Charlatan"
  ],
  "Renari, Merchant of Marvels / Street Urchin": [
    "Renari, Merchant of Marvels",
    "Street Urchin"
  ],
  "Renari, Merchant of Marvels / Sword Coast Sailor": [
    "Renari, Merchant of Marvels",
    "Sword Coast Sailor"
  ],
  "Renari, Merchant of Marvels / Tavern Brawler": [
    "Renari, Merchant of Marvels",
    "Tavern Brawler"
  ],
  "Renari, Merchant of Marvels / Veteran Soldier": [
    "Renari, Merchant of Marvels",
    "Veteran Soldier"
  ],
  "Reyhan, Last of the Abzan / Rograkh, Son of Rohgahh": [
    "Rograkh, Son of Rohgahh",
    "Reyhan, Last of the Abzan"
  ],
  "Reyhan, Last of the Abzan / Sakashima of a Thousand Faces": [
    "Reyhan, Last of the Abzan",
    "Sakashima of a Thousand Faces"
  ],
  "Reyhan, Last of the Abzan / Sengir, the Dark Baron": [
    "Reyhan, Last of the Abzan",
    "Sengir, the Dark Baron"
  ],
  "Reyhan, Last of the Abzan / Siani, Eye of the Storm": [
    "Reyhan, Last of the Abzan",
    "Siani, Eye of the Storm"
  ],
  "Reyhan, Last of the Abzan / Sidar Kondo of Jamuraa": [
    "Reyhan, Last of the Abzan",
    "Sidar Kondo of Jamuraa"
  ],
  "Reyhan, Last of the Abzan / Silas Renn, Seeker Adept": [
    "Reyhan, Last of the Abzan",
    "Silas Renn, Seeker Adept"
  ],
  "Reyhan, Last of the Abzan / Slurrk, All-Ingesting": [
    "Reyhan, Last of the Abzan",
    "Slurrk, All-Ingesting"
  ],
  "Reyhan, Last of the Abzan / Tana, the Bloodsower": [
    "Reyhan, Last of the Abzan",
    "Tana, the Bloodsower"
  ],
  "Reyhan, Last of the Abzan / Tevesh Szat, Doom of Fools": [
    "Reyhan, Last of the Abzan",
    "Tevesh Szat, Doom of Fools"
  ],
  "Reyhan, Last of the Abzan / The Prismatic Piper": [
    "Reyhan, Last of the Abzan",
    "The Prismatic Piper"
  ],
  "Reyhan, Last of the Abzan / Thrasios, Triton Hero": [
    "Reyhan, Last of the Abzan",
    "Thrasios, Triton Hero"
  ],
  "Reyhan, Last of the Abzan / Toggo, Goblin Weaponsmith": [
    "Reyhan, Last of the Abzan",
    "Toggo, Goblin Weaponsmith"
  ],
  "Reyhan, Last of the Abzan / Tormod, the Desecrator": [
    "Reyhan, Last of the Abzan",
    "Tormod, the Desecrator"
  ],
  "Reyhan, Last of the Abzan / Tymna the Weaver": [
    "Reyhan, Last of the Abzan",
    "Tymna the Weaver"
  ],
  "Reyhan, Last of the Abzan / Vial Smasher the Fierce": [
    "Reyhan, Last of the Abzan",
    "Vial Smasher the Fierce"
  ],
  "Reyhan, Last of the Abzan / Yoshimaru, Ever Faithful": [
    "Reyhan, Last of the Abzan",
    "Yoshimaru, Ever Faithful"
  ],
  "Rhoda, Geist Avenger / Timin, Youthful Geist": [
    "Rhoda, Geist Avenger",
    "Timin, Youthful Geist"
  ],
  "Rograkh, Son of Rohgahh / Sakashima of a Thousand Faces": [
    "Rograkh, Son of Rohgahh",
    "Sakashima of a Thousand Faces"
  ],
  "Rograkh, Son of Rohgahh / Sengir, the Dark Baron": [
    "Rograkh, Son of Rohgahh",
    "Sengir, the Dark Baron"
  ],
  "Rograkh, Son of Rohgahh / Siani, Eye of the Storm": [
    "Rograkh, Son of Rohgahh",
    "Siani, Eye of the Storm"
  ],
  "Rograkh, Son of Rohgahh / Sidar Kondo of Jamuraa": [
    "Rograkh, Son of Rohgahh",
    "Sidar Kondo of Jamuraa"
  ],
  "Rograkh, Son of Rohgahh / Silas Renn, Seeker Adept": [
    "Rograkh, Son of Rohgahh",
    "Silas Renn, Seeker Adept"
  ],
  "Rograkh, Son of Rohgahh / Slurrk, All-Ingesting": [
    "Rograkh, Son of Rohgahh",
    "Slurrk, All-Ingesting"
  ],
  "Rograkh, Son of Rohgahh / Tana, the Bloodsower": [
    "Rograkh, Son of Rohgahh",
    "Tana, the Bloodsower"
  ],
  "Rograkh, Son of Rohgahh / Tevesh Szat, Doom of Fools": [
    "Rograkh, Son of Rohgahh",
    "Tevesh Szat, Doom of Fools"
  ],
  "Rograkh, Son of Rohgahh / The Prismatic Piper": [
    "Rograkh, Son of Rohgahh",
    "The Prismatic Piper"
  ],
  "Rograkh, Son of Rohgahh / Thrasios, Triton Hero": [
    "Rograkh, Son of Rohgahh",
    "Thrasios, Triton Hero"
  ],
  "Rograkh, Son of Rohgahh / Toggo, Goblin Weaponsmith": [
    "Rograkh, Son of Rohgahh",
    "Toggo, Goblin Weaponsmith"
  ],
  "Rograkh, Son of Rohgahh / Tormod, the Desecrator": [
    "Rograkh, Son of Rohgahh",
    "Tormod, the Desecrator"
  ],
  "Rograkh, Son of Rohgahh / Tymna the Weaver": [
    "Rograkh, Son of Rohgahh",
    "Tymna the Weaver"
  ],
  "Rograkh, Son of Rohgahh / Vial Smasher the Fierce": [
    "Rograkh, Son of Rohgahh",
    "Vial Smasher the Fierce"
  ],
  "Rograkh, Son of Rohgahh / Yoshimaru, Ever Faithful": [
    "Rograkh, Son of Rohgahh",
    "Yoshimaru, Ever Faithful"
  ],
  "Romana II / The Eighth Doctor": [
    "Romana II",
    "The Eighth Doctor"
  ],
  "Romana II / The Eleventh Doctor": [
    "Romana II",
    "The Eleventh Doctor"
  ],
  "Romana II / The Fifteenth Doctor": [
    "Romana II",
    "The Fifteenth Doctor"
  ],
  "Romana II / The Fifth Doctor": [
    "Romana II",
    "The Fifth Doctor"
  ],
  "Romana II / The First Doctor": [
    "Romana II",
    "The First Doctor"
  ],
  "Romana II / The Fourteenth Doctor": [
    "Romana II",
    "The Fourteenth Doctor"
  ],
  "Romana II / The Fourth Doctor": [
    "Romana II",
    "The Fourth Doctor"
  ],
  "Romana II / The Fugitive Doctor": [
    "Romana II",
    "The Fugitive Doctor"
  ],
  "Romana II / The Ninth Doctor": [
    "Romana II",
    "The Ninth Doctor"
  ],
  "Romana II / The Second Doctor": [
    "Romana II",
    "The Second Doctor"
  ],
  "Romana II / The Seventh Doctor": [
    "Romana II",
    "The Seventh Doctor"
  ],
  "Romana II / The Sixth Doctor": [
    "Romana II",
    "The Sixth Doctor"
  ],
  "Romana II / The Tenth Doctor": [
    "Romana II",
    "The Tenth Doctor"
  ],
  "Romana II / The Third Doctor": [
    "Romana II",
    "The Third Doctor"
  ],
  "Romana II / The Thirteenth Doctor": [
    "Romana II",
    "The Thirteenth Doctor"
  ],
  "Romana II / The Twelfth Doctor": [
    "Romana II",
    "The Twelfth Doctor"
  ],
  "Romana II / The War Doctor": [
    "Romana II",
    "The War Doctor"
  ],
  "Rose Noble / The Eighth Doctor": [
    "Rose Noble",
    "The Eighth Doctor"
  ],
  "Rose Noble / The Eleventh Doctor": [
    "Rose Noble",
    "The Eleventh Doctor"
  ],
  "Rose Noble / The Fifteenth Doctor": [
    "Rose Noble",
    "The Fifteenth Doctor"
  ],
  "Rose Noble / The Fifth Doctor": [
    "Rose Noble",
    "The Fifth Doctor"
  ],
  "Rose Noble / The First Doctor": [
    "Rose Noble",
    "The First Doctor"
  ],
  "Rose Noble / The Fourteenth Doctor": [
    "Rose Noble",
    "The Fourteenth Doctor"
  ],
  "Rose Noble / The Fourth Doctor": [
    "Rose Noble",
    "The Fourth Doctor"
  ],
  "Rose Noble / The Fugitive Doctor": [
    "Rose Noble",
    "The Fugitive Doctor"
  ],
  "Rose Noble / The Ninth Doctor": [
    "Rose Noble",
    "The Ninth Doctor"
  ],
  "Rose Noble / The Second Doctor": [
    "Rose Noble",
    "The Second Doctor"
  ],
  "Rose Noble / The Seventh Doctor": [
    "Rose Noble",
    "The Seventh Doctor"
  ],
  "Rose Noble / The Sixth Doctor": [
    "Rose Noble",
    "The Sixth Doctor"
  ],
  "Rose Noble / The Tenth Doctor": [
    "Rose Noble",
    "The Tenth Doctor"
  ],
  "Rose Noble / The Third Doctor": [
    "Rose Noble",
    "The Third Doctor"
  ],
  "Rose Noble / The Thirteenth Doctor": [
    "Rose Noble",
    "The Thirteenth Doctor"
  ],
  "Rose Noble / The Twelfth Doctor": [
    "Rose Noble",
    "The Twelfth Doctor"
  ],
  "Rose Noble / The War Doctor": [
    "Rose Noble",
    "The War Doctor"
  ],
  "Rose Tyler / The Eighth Doctor": [
    "Rose Tyler",
    "The Eighth Doctor"
  ],
  "Rose Tyler / The Eleventh Doctor": [
    "Rose Tyler",
    "The Eleventh Doctor"
  ],
  "Rose Tyler / The Fifteenth Doctor": [
    "Rose Tyler",
    "The Fifteenth Doctor"
  ],
  "Rose Tyler / The Fifth Doctor": [
    "Rose Tyler",
    "The Fifth Doctor"
  ],
  "Rose Tyler / The First Doctor": [
    "Rose Tyler",
    "The First Doctor"
  ],
  "Rose Tyler / The Fourteenth Doctor": [
    "Rose Tyler",
    "The Fourteenth Doctor"
  ],
  "Rose Tyler / The Fourth Doctor": [
    "Rose Tyler",
    "The Fourth Doctor"
  ],
  "Rose Tyler / The Fugitive Doctor": [
    "Rose Tyler",
    "The Fugitive Doctor"
  ],
  "Rose Tyler / The Ninth Doctor": [
    "Rose Tyler",
    "The Ninth Doctor"
  ],
  "Rose Tyler / The Second Doctor": [
    "Rose Tyler",
    "The Second Doctor"
  ],
  "Rose Tyler / The Seventh Doctor": [
    "Rose Tyler",
    "The Seventh Doctor"
  ],
  "Rose Tyler / The Sixth Doctor": [
    "Rose Tyler",
    "The Sixth Doctor"
  ],
  "Rose Tyler / The Tenth Doctor": [
    "Rose Tyler",
    "The Tenth Doctor"
  ],
  "Rose Tyler / The Third Doctor": [
    "Rose Tyler",
    "The Third Doctor"
  ],
  "Rose Tyler / The Thirteenth Doctor": [
    "Rose Tyler",
    "The Thirteenth Doctor"
  ],
  "Rose Tyler / The Twelfth Doctor": [
    "Rose Tyler",
    "The Twelfth Doctor"
  ],
  "Rose Tyler / The War Doctor": [
    "Rose Tyler",
    "The War Doctor"
  ],
  "Rowan Kenrith / Will Kenrith": [
    "Rowan Kenrith",
    "Will Kenrith"
  ],
  "Ryan Sinclair / The Eighth Doctor": [
    "Ryan Sinclair",
    "The Eighth Doctor"
  ],
  "Ryan Sinclair / The Eleventh Doctor": [
    "Ryan Sinclair",
    "The Eleventh Doctor"
  ],
  "Ryan Sinclair / The Fifteenth Doctor": [
    "Ryan Sinclair",
    "The Fifteenth Doctor"
  ],
  "Ryan Sinclair / The Fifth Doctor": [
    "Ryan Sinclair",
    "The Fifth Doctor"
  ],
  "Ryan Sinclair / The First Doctor": [
    "Ryan Sinclair",
    "The First Doctor"
  ],
  "Ryan Sinclair / The Fourteenth Doctor": [
    "Ryan Sinclair",
    "The Fourteenth Doctor"
  ],
  "Ryan Sinclair / The Fourth Doctor": [
    "Ryan Sinclair",
    "The Fourth Doctor"
  ],
  "Ryan Sinclair / The Fugitive Doctor": [
    "Ryan Sinclair",
    "The Fugitive Doctor"
  ],
  "Ryan Sinclair / The Ninth Doctor": [
    "Ryan Sinclair",
    "The Ninth Doctor"
  ],
  "Ryan Sinclair / The Second Doctor": [
    "Ryan Sinclair",
    "The Second Doctor"
  ],
  "Ryan Sinclair / The Seventh Doctor": [
    "Ryan Sinclair",
    "The Seventh Doctor"
  ],
  "Ryan Sinclair / The Sixth Doctor": [
    "Ryan Sinclair",
    "The Sixth Doctor"
  ],
  "Ryan Sinclair / The Tenth Doctor": [
    "Ryan Sinclair",
    "The Tenth Doctor"
  ],
  "Ryan Sinclair / The Third Doctor": [
    "Ryan Sinclair",
    "The Third Doctor"
  ],
  "Ryan Sinclair / The Thirteenth Doctor": [
    "Ryan Sinclair",
    "The Thirteenth Doctor"
  ],
  "Ryan Sinclair / The Twelfth Doctor": [
    "Ryan Sinclair",
    "The Twelfth Doctor"
  ],
  "Ryan Sinclair / The War Doctor": [
    "Ryan Sinclair",
    "The War Doctor"
  ],
  "Safana, Calimport Cutthroat / Scion of Halaster": [
    "Safana, Calimport Cutthroat",
    "Scion of Halaster"
  ],
  "Safana, Calimport Cutthroat / Shameless Charlatan": [
    "Safana, Calimport Cutthroat",
    "Shameless Charlatan"
  ],
  "Safana, Calimport Cutthroat / Street Urchin": [
    "Safana, Calimport Cutthroat",
    "Street Urchin"
  ],
  "Safana, Calimport Cutthroat / Sword Coast Sailor": [
    "Safana, Calimport Cutthroat",
    "Sword Coast Sailor"
  ],
  "Safana, Calimport Cutthroat / Tavern Brawler": [
    "Safana, Calimport Cutthroat",
    "Tavern Brawler"
  ],
  "Safana, Calimport Cutthroat / Veteran Soldier": [
    "Safana, Calimport Cutthroat",
    "Veteran Soldier"
  ],
  "Sakashima of a Thousand Faces / Sengir, the Dark Baron": [
    "Sakashima of a Thousand Faces",
    "Sengir, the Dark Baron"
  ],
  "Sakashima of a Thousand Faces / Siani, Eye of the Storm": [
    "Sakashima of a Thousand Faces",
    "Siani, Eye of the Storm"
  ],
  "Sakashima of a Thousand Faces / Sidar Kondo of Jamuraa": [
    "Sakashima of a Thousand Faces",
    "Sidar Kondo of Jamuraa"
  ],
  "Sakashima of a Thousand Faces / Silas Renn, Seeker Adept": [
    "Sakashima of a Thousand Faces",
    "Silas Renn, Seeker Adept"
  ],
  "Sakashima of a Thousand Faces / Slurrk, All-Ingesting": [
    "Sakashima of a Thousand Faces",
    "Slurrk, All-Ingesting"
  ],
  "Sakashima of a Thousand Faces / Tana, the Bloodsower": [
    "Sakashima of a Thousand Faces",
    "Tana, the Bloodsower"
  ],
  "Sakashima of a Thousand Faces / Tevesh Szat, Doom of Fools": [
    "Sakashima of a Thousand Faces",
    "Tevesh Szat, Doom of Fools"
  ],
  "Sakashima of a Thousand Faces / The Prismatic Piper": [
    "Sakashima of a Thousand Faces",
    "The Prismatic Piper"
  ],
  "Sakashima of a Thousand Faces / Thrasios, Triton Hero": [
    "Sakashima of a Thousand Faces",
    "Thrasios, Triton Hero"
  ],
  "Sakashima of a Thousand Faces / Toggo, Goblin Weaponsmith": [
    "Sakashima of a Thousand Faces",
    "Toggo, Goblin Weaponsmith"
  ],
  "Sakashima of a Thousand Faces / Tormod, the Desecrator": [
    "Sakashima of a Thousand Faces",
    "Tormod, the Desecrator"
  ],
  "Sakashima of a Thousand Faces / Tymna the Weaver": [
    "Sakashima of a Thousand Faces",
    "Tymna the Weaver"
  ],
  "Sakashima of a Thousand Faces / Vial Smasher the Fierce": [
    "Sakashima of a Thousand Faces",
    "Vial Smasher the Fierce"
  ],
  "Sakashima of a Thousand Faces / Yoshimaru, Ever Faithful": [
    "Sakashima of a Thousand Faces",
    "Yoshimaru, Ever Faithful"
  ],
  "Sarah Jane Smith / The Eighth Doctor": [
    "Sarah Jane Smith",
    "The Eighth Doctor"
  ],
  "Sarah Jane Smith / The Eleventh Doctor": [
    "Sarah Jane Smith",
    "The Eleventh Doctor"
  ],
  "Sarah Jane Smith / The Fifteenth Doctor": [
    "Sarah Jane Smith",
    "The Fifteenth Doctor"
  ],
  "Sarah Jane Smith / The Fifth Doctor": [
    "Sarah Jane Smith",
    "The Fifth Doctor"
  ],
  "Sarah Jane Smith / The First Doctor": [
    "Sarah Jane Smith",
    "The First Doctor"
  ],
  "Sarah Jane Smith / The Fourteenth Doctor": [
    "Sarah Jane Smith",
    "The Fourteenth Doctor"
  ],
  "Sarah Jane Smith / The Fourth Doctor": [
    "Sarah Jane Smith",
    "The Fourth Doctor"
  ],
  "Sarah Jane Smith / The Fugitive Doctor": [
    "Sarah Jane Smith",
    "The Fugitive Doctor"
  ],
  "Sarah Jane Smith / The Ninth Doctor": [
    "Sarah Jane Smith",
    "The Ninth Doctor"
  ],
  "Sarah Jane Smith / The Second Doctor": [
    "Sarah Jane Smith",
    "The Second Doctor"
  ],
  "Sarah Jane Smith / The Seventh Doctor": [
    "Sarah Jane Smith",
    "The Seventh Doctor"
  ],
  "Sarah Jane Smith / The Sixth Doctor": [
    "Sarah Jane Smith",
    "The Sixth Doctor"
  ],
  "Sarah Jane Smith / The Tenth Doctor": [
    "Sarah Jane Smith",
    "The Tenth Doctor"
  ],
  "Sarah Jane Smith / The Third Doctor": [
    "Sarah Jane Smith",
    "The Third Doctor"
  ],
  "Sarah Jane Smith / The Thirteenth Doctor": [
    "Sarah Jane Smith",
    "The Thirteenth Doctor"
  ],
  "Sarah Jane Smith / The Twelfth Doctor": [
    "Sarah Jane Smith",
    "The Twelfth Doctor"
  ],
  "Sarah Jane Smith / The War Doctor": [
    "Sarah Jane Smith",
    "The War Doctor"
  ],
  "Sarevok, Deathbringer / Scion of Halaster": [
    "Sarevok, Deathbringer",
    "Scion of Halaster"
  ],
  "Sarevok, Deathbringer / Shameless Charlatan": [
    "Sarevok, Deathbringer",
    "Shameless Charlatan"
  ],
  "Sarevok, Deathbringer / Street Urchin": [
    "Sarevok, Deathbringer",
    "Street Urchin"
  ],
  "Sarevok, Deathbringer / Sword Coast Sailor": [
    "Sarevok, Deathbringer",
    "Sword Coast Sailor"
  ],
  "Sarevok, Deathbringer / Tavern Brawler": [
    "Sarevok, Deathbringer",
    "Tavern Brawler"
  ],
  "Sarevok, Deathbringer / Veteran Soldier": [
    "Sarevok, Deathbringer",
    "Veteran Soldier"
  ],
  "Scion of Halaster / Shadowheart, Dark Justiciar": [
    "Scion of Halaster",
    "Shadowheart, Dark Justiciar"
  ],
  "Scion of Halaster / Sivriss, Nightmare Speaker": [
    "Scion of Halaster",
    "Sivriss, Nightmare Speaker"
  ],
  "Scion of Halaster / Skanos Dragonheart": [
    "Scion of Halaster",
    "Skanos Dragonheart"
  ],
  "Scion of Halaster / Vhal, Candlekeep Researcher": [
    "Scion of Halaster",
    "Vhal, Candlekeep Researcher"
  ],
  "Scion of Halaster / Viconia, Drow Apostate": [
    "Scion of Halaster",
    "Viconia, Drow Apostate"
  ],
  "Scion of Halaster / Volo, Itinerant Scholar": [
    "Scion of Halaster",
    "Volo, Itinerant Scholar"
  ],
  "Scion of Halaster / Wilson, Refined Grizzly": [
    "Scion of Halaster",
    "Wilson, Refined Grizzly"
  ],
  "Scion of Halaster / Wyll, Blade of Frontiers": [
    "Scion of Halaster",
    "Wyll, Blade of Frontiers"
  ],
  "Scion of Halaster / Zellix, Sanity Flayer": [
    "Scion of Halaster",
    "Zellix, Sanity Flayer"
  ],
  "Sengir, the Dark Baron / Siani, Eye of the Storm": [
    "Sengir, the Dark Baron",
    "Siani, Eye of the Storm"
  ],
  "Sengir, the Dark Baron / Sidar Kondo of Jamuraa": [
    "Sengir, the Dark Baron",
    "Sidar Kondo of Jamuraa"
  ],
  "Sengir, the Dark Baron / Silas Renn, Seeker Adept": [
    "Sengir, the Dark Baron",
    "Silas Renn, Seeker Adept"
  ],
  "Sengir, the Dark Baron / Slurrk, All-Ingesting": [
    "Sengir, the Dark Baron",
    "Slurrk, All-Ingesting"
  ],
  "Sengir, the Dark Baron / Tana, the Bloodsower": [
    "Sengir, the Dark Baron",
    "Tana, the Bloodsower"
  ],
  "Sengir, the Dark Baron / Tevesh Szat, Doom of Fools": [
    "Sengir, the Dark Baron",
    "Tevesh Szat, Doom of Fools"
  ],
  "Sengir, the Dark Baron / The Prismatic Piper": [
    "Sengir, the Dark Baron",
    "The Prismatic Piper"
  ],
  "Sengir, the Dark Baron / Thrasios, Triton Hero": [
    "Sengir, the Dark Baron",
    "Thrasios, Triton Hero"
  ],
  "Sengir, the Dark Baron / Toggo, Goblin Weaponsmith": [
    "Sengir, the Dark Baron",
    "Toggo, Goblin Weaponsmith"
  ],
  "Sengir, the Dark Baron / Tormod, the Desecrator": [
    "Sengir, the Dark Baron",
    "Tormod, the Desecrator"
  ],
  "Sengir, the Dark Baron / Tymna the Weaver": [
    "Sengir, the Dark Baron",
    "Tymna the Weaver"
  ],
  "Sengir, the Dark Baron / Vial Smasher the Fierce": [
    "Sengir, the Dark Baron",
    "Vial Smasher the Fierce"
  ],
  "Sengir, the Dark Baron / Yoshimaru, Ever Faithful": [
    "Sengir, the Dark Baron",
    "Yoshimaru, Ever Faithful"
  ],
  "Shadowheart, Dark Justiciar / Shameless Charlatan": [
    "Shadowheart, Dark Justiciar",
    "Shameless Charlatan"
  ],
  "Shadowheart, Dark Justiciar / Street Urchin": [
    "Shadowheart, Dark Justiciar",
    "Street Urchin"
  ],
  "Shadowheart, Dark Justiciar / Sword Coast Sailor": [
    "Shadowheart, Dark Justiciar",
    "Sword Coast Sailor"
  ],
  "Shadowheart, Dark Justiciar / Tavern Brawler": [
    "Shadowheart, Dark Justiciar",
    "Tavern Brawler"
  ],
  "Shadowheart, Dark Justiciar / Veteran Soldier": [
    "Shadowheart, Dark Justiciar",
    "Veteran Soldier"
  ],
  "Shameless Charlatan / Sivriss, Nightmare Speaker": [
    "Shameless Charlatan",
    "Sivriss, Nightmare Speaker"
  ],
  "Shameless Charlatan / Skanos Dragonheart": [
    "Shameless Charlatan",
    "Skanos Dragonheart"
  ],
  "Shameless Charlatan / Vhal, Candlekeep Researcher": [
    "Shameless Charlatan",
    "Vhal, Candlekeep Researcher"
  ],
  "Shameless Charlatan / Viconia, Drow Apostate": [
    "Shameless Charlatan",
    "Viconia, Drow Apostate"
  ],
  "Shameless Charlatan / Volo, Itinerant Scholar": [
    "Shameless Charlatan",
    "Volo, Itinerant Scholar"
  ],
  "Shameless Charlatan / Wilson, Refined Grizzly": [
    "Shameless Charlatan",
    "Wilson, Refined Grizzly"
  ],
  "Shameless Charlatan / Wyll, Blade of Frontiers": [
    "Shameless Charlatan",
    "Wyll, Blade of Frontiers"
  ],
  "Shameless Charlatan / Zellix, Sanity Flayer": [
    "Shameless Charlatan",
    "Zellix, Sanity Flayer"
  ],
  "Siani, Eye of the Storm / Sidar Kondo of Jamuraa": [
    "Siani, Eye of the Storm",
    "Sidar Kondo of Jamuraa"
  ],
  "Siani, Eye of the Storm / Silas Renn, Seeker Adept": [
    "Siani, Eye of the Storm",
    "Silas Renn, Seeker Adept"
  ],
  "Siani, Eye of the Storm / Slurrk, All-Ingesting": [
    "Siani, Eye of the Storm",
    "Slurrk, All-Ingesting"
  ],
  "Siani, Eye of the Storm / Tana, the Bloodsower": [
    "Siani, Eye of the Storm",
    "Tana, the Bloodsower"
  ],
  "Siani, Eye of the Storm / Tevesh Szat, Doom of Fools": [
    "Siani, Eye of the Storm",
    "Tevesh Szat, Doom of Fools"
  ],
  "Siani, Eye of the Storm / The Prismatic Piper": [
    "Siani, Eye of the Storm",
    "The Prismatic Piper"
  ],
  "Siani, Eye of the Storm / Thrasios, Triton Hero": [
    "Siani, Eye of the Storm",
    "Thrasios, Triton Hero"
  ],
  "Siani, Eye of the Storm / Toggo, Goblin Weaponsmith": [
    "Siani, Eye of the Storm",
    "Toggo, Goblin Weaponsmith"
  ],
  "Siani, Eye of the Storm / Tormod, the Desecrator": [
    "Siani, Eye of the Storm",
    "Tormod, the Desecrator"
  ],
  "Siani, Eye of the Storm / Tymna the Weaver": [
    "Siani, Eye of the Storm",
    "Tymna the Weaver"
  ],
  "Siani, Eye of the Storm / Vial Smasher the Fierce": [
    "Siani, Eye of the Storm",
    "Vial Smasher the Fierce"
  ],
  "Siani, Eye of the Storm / Yoshimaru, Ever Faithful": [
    "Siani, Eye of the Storm",
    "Yoshimaru, Ever Faithful"
  ],
  "Sidar Kondo of Jamuraa / Silas Renn, Seeker Adept": [
    "Sidar Kondo of Jamuraa",
    "Silas Renn, Seeker Adept"
  ],
  "Sidar Kondo of Jamuraa / Slurrk, All-Ingesting": [
    "Sidar Kondo of Jamuraa",
    "Slurrk, All-Ingesting"
  ],
  "Sidar Kondo of Jamuraa / Tana, the Bloodsower": [
    "Sidar Kondo of Jamuraa",
    "Tana, the Bloodsower"
  ],
  "Sidar Kondo of Jamuraa / Tevesh Szat, Doom of Fools": [
    "Sidar Kondo of Jamuraa",
    "Tevesh Szat, Doom of Fools"
  ],
  "Sidar Kondo of Jamuraa / The Prismatic Piper": [
    "Sidar Kondo of Jamuraa",
    "The Prismatic Piper"
  ],
  "Sidar Kondo of Jamuraa / Thrasios, Triton Hero": [
    "Sidar Kondo of Jamuraa",
    "Thrasios, Triton Hero"
  ],
  "Sidar Kondo of Jamuraa / Toggo, Goblin Weaponsmith": [
    "Sidar Kondo of Jamuraa",
    "Toggo, Goblin Weaponsmith"
  ],
  "Sidar Kondo of Jamuraa / Tormod, the Desecrator": [
    "Sidar Kondo of Jamuraa",
    "Tormod, the Desecrator"
  ],
  "Sidar Kondo of Jamuraa / Tymna the Weaver": [
    "Sidar Kondo of Jamuraa",
    "Tymna the Weaver"
  ],
  "Sidar Kondo of Jamuraa / Vial Smasher the Fierce": [
    "Sidar Kondo of Jamuraa",
    "Vial Smasher the Fierce"
  ],
  "Sidar Kondo of Jamuraa / Yoshimaru, Ever Faithful": [
    "Sidar Kondo of Jamuraa",
    "Yoshimaru, Ever Faithful"
  ],
  "Silas Renn, Seeker Adept / Slurrk, All-Ingesting": [
    "Silas Renn, Seeker Adept",
    "Slurrk, All-Ingesting"
  ],
  "Silas Renn, Seeker Adept / Tana, the Bloodsower": [
    "Silas Renn, Seeker Adept",
    "Tana, the Bloodsower"
  ],
  "Silas Renn, Seeker Adept / Tevesh Szat, Doom of Fools": [
    "Silas Renn, Seeker Adept",
    "Tevesh Szat, Doom of Fools"
  ],
  "Silas Renn, Seeker Adept / The Prismatic Piper": [
    "Silas Renn, Seeker Adept",
    "The Prismatic Piper"
  ],
  "Silas Renn, Seeker Adept / Thrasios, Triton Hero": [
    "Silas Renn, Seeker Adept",
    "Thrasios, Triton Hero"
  ],
  "Silas Renn, Seeker Adept / Toggo, Goblin Weaponsmith": [
    "Silas Renn, Seeker Adept",
    "Toggo, Goblin Weaponsmith"
  ],
  "Silas Renn, Seeker Adept / Tormod, the Desecrator": [
    "Silas Renn, Seeker Adept",
    "Tormod, the Desecrator"
  ],
  "Silas Renn, Seeker Adept / Tymna the Weaver": [
    "Silas Renn, Seeker Adept",
    "Tymna the Weaver"
  ],
  "Silas Renn, Seeker Adept / Vial Smasher the Fierce": [
    "Silas Renn, Seeker Adept",
    "Vial Smasher the Fierce"
  ],
  "Silas Renn, Seeker Adept / Yoshimaru, Ever Faithful": [
    "Silas Renn, Seeker Adept",
    "Yoshimaru, Ever Faithful"
  ],
  "Silvar, Devourer of the Free / Trynn, Champion of Freedom": [
    "Silvar, Devourer of the Free",
    "Trynn, Champion of Freedom"
  ],
  "Sivriss, Nightmare Speaker / Street Urchin": [
    "Sivriss, Nightmare Speaker",
    "Street Urchin"
  ],
  "Sivriss, Nightmare Speaker / Sword Coast Sailor": [
    "Sivriss, Nightmare Speaker",
    "Sword Coast Sailor"
  ],
  "Sivriss, Nightmare Speaker / Tavern Brawler": [
    "Sivriss, Nightmare Speaker",
    "Tavern Brawler"
  ],
  "Sivriss, Nightmare Speaker / Veteran Soldier": [
    "Sivriss, Nightmare Speaker",
    "Veteran Soldier"
  ],
  "Skanos Dragonheart / Street Urchin": [
    "Skanos Dragonheart",
    "Street Urchin"
  ],
  "Skanos Dragonheart / Sword Coast Sailor": [
    "Skanos Dragonheart",
    "Sword Coast Sailor"
  ],
  "Skanos Dragonheart / Tavern Brawler": [
    "Skanos Dragonheart",
    "Tavern Brawler"
  ],
  "Skanos Dragonheart / Veteran Soldier": [
    "Skanos Dragonheart",
    "Veteran Soldier"
  ],
  "Slurrk, All-Ingesting / Tana, the Bloodsower": [
    "Slurrk, All-Ingesting",
    "Tana, the Bloodsower"
  ],
  "Slurrk, All-Ingesting / Tevesh Szat, Doom of Fools": [
    "Slurrk, All-Ingesting",
    "Tevesh Szat, Doom of Fools"
  ],
  "Slurrk, All-Ingesting / The Prismatic Piper": [
    "Slurrk, All-Ingesting",
    "The Prismatic Piper"
  ],
  "Slurrk, All-Ingesting / Thrasios, Triton Hero": [
    "Slurrk, All-Ingesting",
    "Thrasios, Triton Hero"
  ],
  "Slurrk, All-Ingesting / Toggo, Goblin Weaponsmith": [
    "Slurrk, All-Ingesting",
    "Toggo, Goblin Weaponsmith"
  ],
  "Slurrk, All-Ingesting / Tormod, the Desecrator": [
    "Slurrk, All-Ingesting",
    "Tormod, the Desecrator"
  ],
  "Slurrk, All-Ingesting / Tymna the Weaver": [
    "Slurrk, All-Ingesting",
    "Tymna the Weaver"
  ],
  "Slurrk, All-Ingesting / Vial Smasher the Fierce": [
    "Slurrk, All-Ingesting",
    "Vial Smasher the Fierce"
  ],
  "Slurrk, All-Ingesting / Yoshimaru, Ever Faithful": [
    "Slurrk, All-Ingesting",
    "Yoshimaru, Ever Faithful"
  ],
  "Sophina, Spearsage Deserter / Wernog, Rider's Chaplain": [
    "Sophina, Spearsage Deserter",
    "Wernog, Rider's Chaplain"
  ],
  "Street Urchin / Vhal, Candlekeep Researcher": [
    "Street Urchin",
    "Vhal, Candlekeep Researcher"
  ],
  "Street Urchin / Viconia, Drow Apostate": [
    "Street Urchin",
    "Viconia, Drow Apostate"
  ],
  "Street Urchin / Volo, Itinerant Scholar": [
    "Street Urchin",
    "Volo, Itinerant Scholar"
  ],
  "Street Urchin / Wilson, Refined Grizzly": [
    "Street Urchin",
    "Wilson, Refined Grizzly"
  ],
  "Street Urchin / Wyll, Blade of Frontiers": [
    "Street Urchin",
    "Wyll, Blade of Frontiers"
  ],
  "Street Urchin / Zellix, Sanity Flayer": [
    "Street Urchin",
    "Zellix, Sanity Flayer"
  ],
  "Susan Foreman / The Eighth Doctor": [
    "Susan Foreman",
    "The Eighth Doctor"
  ],
  "Susan Foreman / The Eleventh Doctor": [
    "Susan Foreman",
    "The Eleventh Doctor"
  ],
  "Susan Foreman / The Fifteenth Doctor": [
    "Susan Foreman",
    "The Fifteenth Doctor"
  ],
  "Susan Foreman / The Fifth Doctor": [
    "Susan Foreman",
    "The Fifth Doctor"
  ],
  "Susan Foreman / The First Doctor": [
    "Susan Foreman",
    "The First Doctor"
  ],
  "Susan Foreman / The Fourteenth Doctor": [
    "Susan Foreman",
    "The Fourteenth Doctor"
  ],
  "Susan Foreman / The Fourth Doctor": [
    "Susan Foreman",
    "The Fourth Doctor"
  ],
  "Susan Foreman / The Fugitive Doctor": [
    "Susan Foreman",
    "The Fugitive Doctor"
  ],
  "Susan Foreman / The Ninth Doctor": [
    "Susan Foreman",
    "The Ninth Doctor"
  ],
  "Susan Foreman / The Second Doctor": [
    "Susan Foreman",
    "The Second Doctor"
  ],
  "Susan Foreman / The Seventh Doctor": [
    "Susan Foreman",
    "The Seventh Doctor"
  ],
  "Susan Foreman / The Sixth Doctor": [
    "Susan Foreman",
    "The Sixth Doctor"
  ],
  "Susan Foreman / The Tenth Doctor": [
    "Susan Foreman",
    "The Tenth Doctor"
  ],
  "Susan Foreman / The Third Doctor": [
    "Susan Foreman",
    "The Third Doctor"
  ],
  "Susan Foreman / The Thirteenth Doctor": [
    "Susan Foreman",
    "The Thirteenth Doctor"
  ],
  "Susan Foreman / The Twelfth Doctor": [
    "Susan Foreman",
    "The Twelfth Doctor"
  ],
  "Susan Foreman / The War Doctor": [
    "Susan Foreman",
    "The War Doctor"
  ],
  "Sword Coast Sailor / Vhal, Candlekeep Researcher": [
    "Sword Coast Sailor",
    "Vhal, Candlekeep Researcher"
  ],
  "Sword Coast Sailor / Viconia, Drow Apostate": [
    "Sword Coast Sailor",
    "Viconia, Drow Apostate"
  ],
  "Sword Coast Sailor / Volo, Itinerant Scholar": [
    "Sword Coast Sailor",
    "Volo, Itinerant Scholar"
  ],
  "Sword Coast Sailor / Wilson, Refined Grizzly": [
    "Sword Coast Sailor",
    "Wilson, Refined Grizzly"
  ],
  "Sword Coast Sailor / Wyll, Blade of Frontiers": [
    "Sword Coast Sailor",
    "Wyll, Blade of Frontiers"
  ],
  "Sword Coast Sailor / Zellix, Sanity Flayer": [
    "Sword Coast Sailor",
    "Zellix, Sanity Flayer"
  ],
  "Tana, the Bloodsower / Tevesh Szat, Doom of Fools": [
    "Tana, the Bloodsower",
    "Tevesh Szat, Doom of Fools"
  ],
  "Tana, the Bloodsower / The Prismatic Piper": [
    "Tana, the Bloodsower",
    "The Prismatic Piper"
  ],
  "Tana, the Bloodsower / Thrasios, Triton Hero": [
    "Tana, the Bloodsower",
    "Thrasios, Triton Hero"
  ],
  "Tana, the Bloodsower / Toggo, Goblin Weaponsmith": [
    "Tana, the Bloodsower",
    "Toggo, Goblin Weaponsmith"
  ],
  "Tana, the Bloodsower / Tormod, the Desecrator": [
    "Tana, the Bloodsower",
    "Tormod, the Desecrator"
  ],
  "Tana, the Bloodsower / Tymna the Weaver": [
    "Tymna the Weaver",
    "Tana, the Bloodsower"
  ],
  "Tana, the Bloodsower / Vial Smasher the Fierce": [
    "Tana, the Bloodsower",
    "Vial Smasher the Fierce"
  ],
  "Tana, the Bloodsower / Yoshimaru, Ever Faithful": [
    "Tana, the Bloodsower",
    "Yoshimaru, Ever Faithful"
  ],
  "Tavern Brawler / Vhal, Candlekeep Researcher": [
    "Tavern Brawler",
    "Vhal, Candlekeep Researcher"
  ],
  "Tavern Brawler / Viconia, Drow Apostate": [
    "Tavern Brawler",
    "Viconia, Drow Apostate"
  ],
  "Tavern Brawler / Volo, Itinerant Scholar": [
    "Tavern Brawler",
    "Volo, Itinerant Scholar"
  ],
  "Tavern Brawler / Wilson, Refined Grizzly": [
    "Tavern Brawler",
    "Wilson, Refined Grizzly"
  ],
  "Tavern Brawler / Wyll, Blade of Frontiers": [
    "Tavern Brawler",
    "Wyll, Blade of Frontiers"
  ],
  "Tavern Brawler / Zellix, Sanity Flayer": [
    "Tavern Brawler",
    "Zellix, Sanity Flayer"
  ],
  "Tegan Jovanka / The Eighth Doctor": [
    "Tegan Jovanka",
    "The Eighth Doctor"
  ],
  "Tegan Jovanka / The Eleventh Doctor": [
    "Tegan Jovanka",
    "The Eleventh Doctor"
  ],
  "Tegan Jovanka / The Fifteenth Doctor": [
    "Tegan Jovanka",
    "The Fifteenth Doctor"
  ],
  "Tegan Jovanka / The Fifth Doctor": [
    "Tegan Jovanka",
    "The Fifth Doctor"
  ],
  "Tegan Jovanka / The First Doctor": [
    "Tegan Jovanka",
    "The First Doctor"
  ],
  "Tegan Jovanka / The Fourteenth Doctor": [
    "Tegan Jovanka",
    "The Fourteenth Doctor"
  ],
  "Tegan Jovanka / The Fourth Doctor": [
    "Tegan Jovanka",
    "The Fourth Doctor"
  ],
  "Tegan Jovanka / The Fugitive Doctor": [
    "Tegan Jovanka",
    "The Fugitive Doctor"
  ],
  "Tegan Jovanka / The Ninth Doctor": [
    "Tegan Jovanka",
    "The Ninth Doctor"
  ],
  "Tegan Jovanka / The Second Doctor": [
    "Tegan Jovanka",
    "The Second Doctor"
  ],
  "Tegan Jovanka / The Seventh Doctor": [
    "Tegan Jovanka",
    "The Seventh Doctor"
  ],
  "Tegan Jovanka / The Sixth Doctor": [
    "Tegan Jovanka",
    "The Sixth Doctor"
  ],
  "Tegan Jovanka / The Tenth Doctor": [
    "Tegan Jovanka",
    "The Tenth Doctor"
  ],
  "Tegan Jovanka / The Third Doctor": [
    "Tegan Jovanka",
    "The Third Doctor"
  ],
  "Tegan Jovanka / The Thirteenth Doctor": [
    "Tegan Jovanka",
    "The Thirteenth Doctor"
  ],
  "Tegan Jovanka / The Twelfth Doctor": [
    "Tegan Jovanka",
    "The Twelfth Doctor"
  ],
  "Tegan Jovanka / The War Doctor": [
    "Tegan Jovanka",
    "The War Doctor"
  ],
  "Tevesh Szat, Doom of Fools / The Prismatic Piper": [
    "Tevesh Szat, Doom of Fools",
    "The Prismatic Piper"
  ],
  "Tevesh Szat, Doom of Fools / Thrasios, Triton Hero": [
    "Tevesh Szat, Doom of Fools",
    "Thrasios, Triton Hero"
  ],
  "Tevesh Szat, Doom of Fools / Toggo, Goblin Weaponsmith": [
    "Tevesh Szat, Doom of Fools",
    "Toggo, Goblin Weaponsmith"
  ],
  "Tevesh Szat, Doom of Fools / Tormod, the Desecrator": [
    "Tevesh Szat, Doom of Fools",
    "Tormod, the Desecrator"
  ],
  "Tevesh Szat, Doom of Fools / Tymna the Weaver": [
    "Tevesh Szat, Doom of Fools",
    "Tymna the Weaver"
  ],
  "Tevesh Szat, Doom of Fools / Vial Smasher the Fierce": [
    "Tevesh Szat, Doom of Fools",
    "Vial Smasher the Fierce"
  ],
  "Tevesh Szat, Doom of Fools / Yoshimaru, Ever Faithful": [
    "Tevesh Szat, Doom of Fools",
    "Yoshimaru, Ever Faithful"
  ],
  "The Eighth Doctor / Vislor Turlough": [
    "The Eighth Doctor",
    "Vislor Turlough"
  ],
  "The Eighth Doctor / Yasmin Khan": [
    "The Eighth Doctor",
    "Yasmin Khan"
  ],
  "The Eleventh Doctor / Vislor Turlough": [
    "The Eleventh Doctor",
    "Vislor Turlough"
  ],
  "The Eleventh Doctor / Yasmin Khan": [
    "The Eleventh Doctor",
    "Yasmin Khan"
  ],
  "The Fifteenth Doctor / Vislor Turlough": [
    "The Fifteenth Doctor",
    "Vislor Turlough"
  ],
  "The Fifteenth Doctor / Yasmin Khan": [
    "The Fifteenth Doctor",
    "Yasmin Khan"
  ],
  "The Fifth Doctor / Vislor Turlough": [
    "The Fifth Doctor",
    "Vislor Turlough"
  ],
  "The Fifth Doctor / Yasmin Khan": [
    "The Fifth Doctor",
    "Yasmin Khan"
  ],
  "The First Doctor / Vislor Turlough": [
    "The First Doctor",
    "Vislor Turlough"
  ],
  "The First Doctor / Yasmin Khan": [
    "The First Doctor",
    "Yasmin Khan"
  ],
  "The Fourteenth Doctor / Vislor Turlough": [
    "The Fourteenth Doctor",
    "Vislor Turlough"
  ],
  "The Fourteenth Doctor / Yasmin Khan": [
    "The Fourteenth Doctor",
    "Yasmin Khan"
  ],
  "The Fourth Doctor / Vislor Turlough": [
    "The Fourth Doctor",
    "Vislor Turlough"
  ],
  "The Fourth Doctor / Yasmin Khan": [
    "The Fourth Doctor",
    "Yasmin Khan"
  ],
  "The Fugitive Doctor / Vislor Turlough": [
    "The Fugitive Doctor",
    "Vislor Turlough"
  ],
  "The Fugitive Doctor / Yasmin Khan": [
    "The Fugitive Doctor",
    "Yasmin Khan"
  ],
  "The Ninth Doctor / Vislor Turlough": [
    "The Ninth Doctor",
    "Vislor Turlough"
  ],
  "The Ninth Doctor / Yasmin Khan": [
    "The Ninth Doctor",
    "Yasmin Khan"
  ],
  "The Prismatic Piper / Thrasios, Triton Hero": [
    "The Prismatic Piper",
    "Thrasios, Triton Hero"
  ],
  "The Prismatic Piper / Toggo, Goblin Weaponsmith": [
    "The Prismatic Piper",
    "Toggo, Goblin Weaponsmith"
  ],
  "The Prismatic Piper / Tormod, the Desecrator": [
    "The Prismatic Piper",
    "Tormod, the Desecrator"
  ],
  "The Prismatic Piper / Tymna the Weaver": [
    "The Prismatic Piper",
    "Tymna the Weaver"
  ],
  "The Prismatic Piper / Vial Smasher the Fierce": [
    "The Prismatic Piper",
    "Vial Smasher the Fierce"
  ],
  "The Prismatic Piper / Yoshimaru, Ever Faithful": [
    "The Prismatic Piper",
    "Yoshimaru, Ever Faithful"
  ],
  "The Second Doctor / Vislor Turlough": [
    "The Second Doctor",
    "Vislor Turlough"
  ],
  "The Second Doctor / Yasmin Khan": [
    "The Second Doctor",
    "Yasmin Khan"
  ],
  "The Seventh Doctor / Vislor Turlough": [
    "The Seventh Doctor",
    "Vislor Turlough"
  ],
  "The Seventh Doctor / Yasmin Khan": [
    "The Seventh Doctor",
    "Yasmin Khan"
  ],
  "The Sixth Doctor / Vislor Turlough": [
    "The Sixth Doctor",
    "Vislor Turlough"
  ],
  "The Sixth Doctor / Yasmin Khan": [
    "The Sixth Doctor",
    "Yasmin Khan"
  ],
  "The Tenth Doctor / Vislor Turlough": [
    "The Tenth Doctor",
    "Vislor Turlough"
  ],
  "The Tenth Doctor / Yasmin Khan": [
    "The Tenth Doctor",
    "Yasmin Khan"
  ],
  "The Third Doctor / Vislor Turlough": [
    "The Third Doctor",
    "Vislor Turlough"
  ],
  "The Third Doctor / Yasmin Khan": [
    "The Third Doctor",
    "Yasmin Khan"
  ],
  "The Thirteenth Doctor / Vislor Turlough": [
    "The Thirteenth Doctor",
    "Vislor Turlough"
  ],
  "The Thirteenth Doctor / Yasmin Khan": [
    "The Thirteenth Doctor",
    "Yasmin Khan"
  ],
  "The Twelfth Doctor / Vislor Turlough": [
    "The Twelfth Doctor",
    "Vislor Turlough"
  ],
  "The Twelfth Doctor / Yasmin Khan": [
    "The Twelfth Doctor",
    "Yasmin Khan"
  ],
  "The War Doctor / Vislor Turlough": [
    "The War Doctor",
    "Vislor Turlough"
  ],
  "The War Doctor / Yasmin Khan": [
    "The War Doctor",
    "Yasmin Khan"
  ],
  "Thrasios, Triton Hero / Toggo, Goblin Weaponsmith": [
    "Thrasios, Triton Hero",
    "Toggo, Goblin Weaponsmith"
  ],
  "Thrasios, Triton Hero / Tormod, the Desecrator": [
    "Thrasios, Triton Hero",
    "Tormod, the Desecrator"
  ],
  "Thrasios, Triton Hero / Tymna the Weaver": [
    "Tymna the Weaver",
    "Thrasios, Triton Hero"
  ],
  "Thrasios, Triton Hero / Vial Smasher the Fierce": [
    "Thrasios, Triton Hero",
    "Vial Smasher the Fierce"
  ],
  "Thrasios, Triton Hero / Yoshimaru, Ever Faithful": [
    "Thrasios, Triton Hero",
    "Yoshimaru, Ever Faithful"
  ],
  "Toggo, Goblin Weaponsmith / Tormod, the Desecrator": [
    "Toggo, Goblin Weaponsmith",
    "Tormod, the Desecrator"
  ],
  "Toggo, Goblin Weaponsmith / Tymna the Weaver": [
    "Toggo, Goblin Weaponsmith",
    "Tymna the Weaver"
  ],
  "Toggo, Goblin Weaponsmith / Vial Smasher the Fierce": [
    "Toggo, Goblin Weaponsmith",
    "Vial Smasher the Fierce"
  ],
  "Toggo, Goblin Weaponsmith / Yoshimaru, Ever Faithful": [
    "Toggo, Goblin Weaponsmith",
    "Yoshimaru, Ever Faithful"
  ],
  "Tormod, the Desecrator / Tymna the Weaver": [
    "Tormod, the Desecrator",
    "Tymna the Weaver"
  ],
  "Tormod, the Desecrator / Vial Smasher the Fierce": [
    "Tormod, the Desecrator",
    "Vial Smasher the Fierce"
  ],
  "Tormod, the Desecrator / Yoshimaru, Ever Faithful": [
    "Tormod, the Desecrator",
    "Yoshimaru, Ever Faithful"
  ],
  "Tymna the Weaver / Vial Smasher the Fierce": [
    "Tymna the Weaver",
    "Vial Smasher the Fierce"
  ],
  "Tymna the Weaver / Yoshimaru, Ever Faithful": [
    "Tymna the Weaver",
    "Yoshimaru, Ever Faithful"
  ],
  "Veteran Soldier / Vhal, Candlekeep Researcher": [
    "Veteran Soldier",
    "Vhal, Candlekeep Researcher"
  ],
  "Veteran Soldier / Viconia, Drow Apostate": [
    "Veteran Soldier",
    "Viconia, Drow Apostate"
  ],
  "Veteran Soldier / Volo, Itinerant Scholar": [
    "Veteran Soldier",
    "Volo, Itinerant Scholar"
  ],
  "Veteran Soldier / Wilson, Refined Grizzly": [
    "Veteran Soldier",
    "Wilson, Refined Grizzly"
  ],
  "Veteran Soldier / Wyll, Blade of Frontiers": [
    "Veteran Soldier",
    "Wyll, Blade of Frontiers"
  ],
  "Veteran Soldier / Zellix, Sanity Flayer": [
    "Veteran Soldier",
    "Zellix, Sanity Flayer"
  ],
  "Vial Smasher the Fierce / Yoshimaru, Ever Faithful": [
    "Vial Smasher the Fierce",
    "Yoshimaru, Ever Faithful"
  ]
}$partner_order$::jsonb);

CREATE FUNCTION public.canonical_commander_components(names text[])
RETURNS text[] LANGUAGE sql STABLE SET search_path = public AS $$
  WITH cleaned AS (
    SELECT btrim(split_part(split_part(
      replace(replace(replace(replace(
        replace(replace(n.name, chr(92)||chr(39), chr(39)), chr(92)||chr(34), chr(34)),
        chr(8217), chr(39)), chr(8216), chr(39)), chr(8220), chr(34)), chr(8221), chr(34)),
      ' // ',1),'[',1)) AS name,n.position
    FROM unnest(names) WITH ORDINALITY AS n(name,position)
  ), resolved AS (
    SELECT coalesce(a.canonical_name,n.name) AS name,n.position
    FROM cleaned n
    LEFT JOIN public.commander_name_aliases a ON a.alias=n.name
  ), arrays AS (
    SELECT array_agg(name ORDER BY position) AS original,
      array_agg(name ORDER BY name COLLATE "C") AS sorted FROM resolved
  )
  SELECT CASE WHEN cardinality(original)=2 THEN
    coalesce((SELECT commander_names FROM public.commander_pair_display_order
      WHERE pair_key=array_to_string(sorted,' / ')),sorted)
    ELSE original END FROM arrays;
$$;

CREATE FUNCTION public.normalize_commander_alias()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
DECLARE resolved text[];
BEGIN
  resolved := public.canonical_commander_components(NEW.commander_names);
  IF cardinality(NEW.scryfall_ids)=cardinality(NEW.commander_names) THEN
    NEW.scryfall_ids := ARRAY(
      SELECT NEW.scryfall_ids[n.position::int]
      FROM unnest(NEW.commander_names) WITH ORDINALITY n(name,position)
      ORDER BY array_position(resolved,(public.canonical_commander_components(ARRAY[n.name]))[1])
    );
  END IF;
  NEW.commander_names := resolved;
  NEW.name := array_to_string(NEW.commander_names,' / ');
  RETURN NEW;
END;
$$;
CREATE TRIGGER normalize_commander_alias
BEFORE INSERT OR UPDATE OF name, commander_names ON public.commanders
FOR EACH ROW EXECUTE FUNCTION public.normalize_commander_alias();

-- Repoint base facts, including partner pairs; never sum overlapping summaries.
DO $$
DECLARE source record; target_id uuid; resolved text[];
BEGIN
  FOR source IN
    SELECT c.* FROM public.commanders c
    WHERE c.commander_names IS DISTINCT FROM public.canonical_commander_components(c.commander_names)
       OR c.name IS DISTINCT FROM array_to_string(public.canonical_commander_components(c.commander_names),' / ')
       OR EXISTS (SELECT 1 FROM public.commander_name_aliases a WHERE a.alias=ANY(string_to_array(c.name,' / ')))
  LOOP
    resolved := public.canonical_commander_components(source.commander_names);
    INSERT INTO public.commanders(name,commander_names,scryfall_ids,color_identity,archetype,win_condition,notes)
    VALUES (array_to_string(resolved,' / '),source.commander_names,source.scryfall_ids,source.color_identity,source.archetype,source.win_condition,source.notes)
    ON CONFLICT(name) DO UPDATE SET commander_names=excluded.commander_names,
      scryfall_ids=CASE WHEN commanders.id=source.id THEN excluded.scryfall_ids
        ELSE coalesce(commanders.scryfall_ids,excluded.scryfall_ids) END,
      color_identity=coalesce(commanders.color_identity,excluded.color_identity),
      archetype=coalesce(commanders.archetype,excluded.archetype),
      win_condition=coalesce(commanders.win_condition,excluded.win_condition),
      notes=coalesce(commanders.notes,excluded.notes)
    RETURNING id INTO target_id;
    IF target_id <> source.id THEN
      UPDATE public.tournament_entries SET commander_id=target_id WHERE commander_id=source.id;
      UPDATE public.commander_matchups SET commander_id=target_id WHERE commander_id=source.id;
      UPDATE public.commander_matchups SET opponent_commander_id=target_id WHERE opponent_commander_id=source.id;
      DELETE FROM public.commanders WHERE id=source.id;
    END IF;
  END LOOP;
END;
$$;

-- Run with consolidate_names.py so derived regional/commander summaries and
-- materialized views refresh in this transaction. Ratings/events are untouched.
