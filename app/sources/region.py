"""Region tagging helpers."""
import re

# Map a location string to a region. Order matters: more specific first.
# Matching uses word boundaries so "Chester" doesn't match "Colchester".
_REGION_RULES = [
    ("manchester", [
        "manchester", "salford", "bolton", "bury", "oldham", "rochdale",
        "stockport", "tameside", "trafford", "wigan", "greater manchester",
        "ashton-under-lyne", "ashton under lyne", "middleton", "hyde",
        "denton", "stalybridge", "glossop", "altrincham", "sale", "eccles",
        "swinton", "leigh", "atherton", "tyldesley", "ramsbottom", "radcliffe",
        "farnworth", "westhoughton", "horwich", "blackrod", "marple",
        "hazel grove", "wilmslow", "cheadle", "gatley", "didsbury",
        "chorlton", "fallowfield", "withington", "prestwich", "whitefield",
        "heywood", "littleborough", "milnrow", "shaw", "royton", "chadderton",
        "failsworth", "droylsden", "audenshaw", "reddish", "brinnington",
        "hattersley", "mottram", "broadbottom", "new mills",
    ]),
    ("leeds", [
        "leeds", "bradford", "huddersfield", "halifax", "wakefield",
        "west yorkshire", "york", "otley", "dewsbury", "harrogate", "ilkley",
        "skipton", "keighley", "castleford", "pontefract", "morley", "pudsey",
        "wetherby", "selby", "ripon", "garforth", "horsforth", "guiseley",
        "yeadon", "rawdon", "calverley", "bramley", "armley", "headingley",
        "roundhay", "crossgates", "kippax", "swillington", "rothwell",
        "tadcaster", "knaresborough", "bingley", "shipley", "baildon",
        "queensbury", "sowerby bridge", "hebden bridge", "todmorden",
        "brighouse", "elland", "mirfield", "cleckheaton", "heckmondwike",
        "liversedge", "ossett", "normanton", "featherstone", "hemsworth",
        "south elmsall", "knottingley", "sowerby",
    ]),
    ("liverpool", [
        "liverpool", "wirral", "sefton", "knowsley", "st helens",
        "merseyside", "bootle", "crosby", "maghull", "kirkby", "prescot",
        "huyton", "widnes", "runcorn", "ellesmere port", "birkenhead",
        "wallasey", "west kirby", "hoylake", "southport", "ormskirk",
        "skelmersdale", "newton-le-willows", "newton le willows", "rainford",
        "thatto heath", "speke", "aigburth", "allerton", "childwall",
        "wavertree", "west derby", "walton", "anfield", "everton", "toxteth",
    ]),
    ("sheffield", [
        "sheffield", "rotherham", "doncaster", "barnsley", "south yorkshire",
        "chesterfield", "worksop", "matlock", "bakewell", "dronfield",
        "chapeltown", "ecclesfield", "handsworth", "woodhouse", "beighton",
        "crystal peaks", "meadowhall", "mexborough", "swinton", "wath",
        "hoyland", "wombwell", "goldthorpe", "thurnscoe", "conisbrough",
        "maltby", "dinnington", "kilnhurst", "rawmarsh", "hatfield",
    ]),
    ("nw", [
        "lancashire", "preston", "blackburn", "burnley", "blackpool",
        "warrington", "chester", "crewe", "cumbria", "carlisle", "north west",
        "cheshire", "lancaster", "morecambe", "lytham", "fleetwood", "chorley",
        "leyland", "accrington", "nelson", "colne", "clitheroe", "darwen",
        "rawtenstall", "haslingden", "bacup", "rossendale", "kendal",
        "penrith", "whitehaven", "workington", "keswick", "ulverston",
        "barrow-in-furness", "barrow in furness", "windermere", "ambleside",
        "cockermouth", "maryport", "wigton", "appleby", "sedbergh",
        "milnthorpe", "carnforth", "garstang", "longridge", "kirkham",
        "freckleton", "thornton", "cleveleys", "poulton-le-fylde",
        "poulton le fylde", "st annes", "nantwich", "macclesfield",
        "congleton", "knutsford", "northwich", "winsford", "middlewich",
        "sandbach", "alsager", "holmes chapel", "poynton", "disley",
        "handforth", "poynton", "aughton", "burscough", "tarleton",
        "parbold", "euxton", "adlington", "coppull", "standish",
    ]),
]

_COMPILED = [
    (region, [re.compile(r"\b" + re.escape(kw) + r"\b", re.I) for kw in kws])
    for region, kws in _REGION_RULES
]


def tag_region(location: str) -> str:
    """Return a region tag for a location string, or 'other'."""
    if not location:
        return "other"
    for region, patterns in _COMPILED:
        for pat in patterns:
            if pat.search(location):
                return region
    return "other"


def normalize_location(location: str) -> str:
    """Strip postcodes and tidy a location string for display."""
    if not location:
        return ""
    # Remove bracketed postcodes like "(M1 2AB)"
    cleaned = re.sub(r"\([^)]*\)", "", location)
    cleaned = re.sub(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,-")
    return cleaned
