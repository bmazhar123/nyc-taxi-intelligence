\# Phase 1 Notes — What the Raw Data Actually Looks Like



\*\*Data:\*\* NYC TLC yellow taxi trips, January 2024

\*\*Rows:\*\* 2,964,624

\*\*Date inspected:\*\* November 6, 2026



Before cleaning anything, I wanted to measure what was wrong with the raw

file so every cleaning rule in Phase 2 has a number behind it. Nothing has

been removed yet; everything below is a count from the untouched file.



\## The good news first



The file is cleaner than I expected in a few important ways. There are no

exact duplicate rows, every VendorID, RatecodeID, and payment\_type code

matches the official data dictionary, and every pickup and drop-off zone

exists in the zone lookup table.



\## Missing values: one group, not random gaps



140,162 trips (4.73%) are missing the same five fields at once:

passenger\_count, RatecodeID, store\_and\_fwd\_flag, congestion\_surcharge, and

Airport\_fee. My first guess was that these were the same rows, and a

follow-up query confirmed it: all 140,162 are missing all five together.



Every one of those rows has payment\_type 0, which the data dictionary

defines as a "Flex Fare trip." They come from three vendors (91,447 from

vendor 2, 48,455 from vendor 1, and 260 from vendor 6), so this isn't one

vendor sending bad data. It looks like Flex Fare trips are simply reported

without these fields.



I'm keeping these rows. Deleting them would quietly erase almost 5% of real

trips and make demand look lower than it was. Instead, I'll treat the

missing values as "unknown," not zero. A missing congestion surcharge

doesn't mean the charge was $0; it means the record doesn't say.



Still to check: I've shown that every null row is a Flex Fare trip, but not

that every Flex Fare trip has nulls. I'll check the reverse in Phase 2.



\## Negative money values: mostly reversals, not typos



35,504 trips (1.20%) have a negative total\_amount. Broken down by payment

type: 21,406 disputes, 8,326 cash, 5,741 no-charge, 29 credit card, and 2

Flex Fare. Disputes and no-charge trips together make up about 76% of

them, which points to refunds and adjustments, not data entry errors.



The most useful thing I found was a single trip recorded twice: once at

\-$10.50 and once at +$10.50, same timestamps and distance. That looks like

an original charge plus a reversal that cancels it out. If that pattern is

common, I can't just delete negative rows. Dropping the -$10.50 and keeping

the +$10.50 would count money that was never actually collected. In Phase 2

I'll measure how many negative rows have a matching positive "twin" before

deciding how to handle them.



\## Timestamps



18 trips have a pickup time outside January:



\- \*\*5 are clearly bad clocks:\*\* 2 dated December 31, 2002 (the ±$10.50

&#x20; pair above) and 3 dated January 1, 2009. My guess is that a meter

&#x20; reset to a default date, but I can't confirm that from the data alone.

\- \*\*13 are real trips near the month boundary:\*\* 10 started late on

&#x20; December 31, 2023, and 3 started in the first minute or so of

&#x20; February 1, 2024.



I'll keep only trips whose pickup falls inside the study period. The

boundary trips belong to December or February, and once I load all six

months, leaving them in would risk counting the same period twice.



I also found 870 trips where the drop-off time is at or before the pickup

time, and 16 trips longer than 24 hours. Both are physically impossible

and very few in number, so they'll be removed with the counts logged.



\## Other things to handle in Phase 2



\- \*\*Zero-distance trips: 60,371 (2.04%).\*\* These aren't automatically

&#x20; wrong. They could be cancellations, meter glitches, or flat-rate fares.

&#x20; I'll look at their fares and rate codes before deciding anything.

\- \*\*Zero passengers: 31,465 (1.06%).\*\* Passenger count is entered by the

&#x20; driver, so it's not reliable. I'll keep the trips but leave them out of

&#x20; any per-passenger metric.

\- \*\*Catch-all zones:\*\* zone 264 is "Unknown" and zone 265 is "Outside of

&#x20; NYC." They're valid codes but not real places, so I'll keep the trips

&#x20; and exclude these zones from maps and zone rankings.



\## Schema



The file names its column "Airport\_fee," but the data dictionary spells it

"airport\_fee." My inspection script compares column names

case-insensitively, so it flagged the difference instead of reporting the

column as missing. In Phase 2 I'll rename it to match the dictionary, so

the column name is consistent no matter which month a file comes from.



\## What I'd say in an interview



I measured before cleaning. The two biggest issues (missing fields and

negative charges) turned out to be patterns in how certain trip types are

reported, not random errors, and that changed how I handle them. Deleting

those rows would have made the numbers worse.

