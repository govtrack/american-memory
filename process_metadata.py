#!/usr/bin/env python

# Convert the American Memory Century of Lawmaking metadata files for
# House and Senate bills and resolutions (llhb, llsb, llsr) into CSV
# format (comma-delimited, quote-quoted, and UTF-8 encoded) and JSON
# format.
#
# The original metadata files are tricky to parse for two reasons.
# First, it's not really a CSV or it's not constructed correctly.
# Regexes must be used to find column boundaries. Second, the character
# encoding is IBM Code Page 850.
#
# This script was written originally by Gordon Hemsley. Modified by
# Joshua Tauberer.

import glob, re, csv, json, datetime


# Because of issues with unescaped quotes, we can't use a normal CSV parser.
# Instead, we construct a regular expression based on the expected values of each field.

fields = {
	"llhb": [ ( "collection", None, r"llhb" ), ( "volume", None, r"[0-9]{3}" ), ( "image", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
	"llsb": [ ( "collection", None, r"llsb" ), ( "volume", None, r"[0-9]{3}" ), ( "image", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
	"llsr": [ ( "collection", None, r"llsr" ), ( "volume", None, r"[0-9]{3}" ), ( "image", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
}
	
collection_regex = { }

for collection in fields:
	regexp_pieces = []
	
	for field_data in fields[collection]:
		field, separator, data_pattern = field_data
		if separator:
			field_pattern = r'(' + data_pattern + r"(?:" + separator + data_pattern + r')*)'
		else:
			field_pattern = r'(' + data_pattern + r')'

		regexp_pieces.append(r'"(?:' + field_pattern + r'|)"')

	collection_regex[collection] = re.compile(",".join(regexp_pieces))
	
def parse_date(dd):
	y, m, d = re.match(r"(\d\d\d\d)(\d\d)(\d\d)$", dd).groups()
	try:
		return datetime.date(int(y), int(m), int(d)).isoformat()
	except ValueError:
		print "Invalid date:", dd
		return "%s-%s-%s" % (y, m, d)
	
# Process the files.

for fn in sorted(glob.glob("source/*")):
	print fn, "..."
	
	m = re.match(r"source/(llhb|llsb|llsr)(\d+)\.txt$", fn)
	if not m: raise ValueError("Invalid file name: " + fn)
	
	collection = m.group(1)
	volume = int(m.group(2))
	data = []
	
	with open(fn) as txt_file:
		for line in txt_file:
			# Ignore blank lines.
			if line.strip() == "":
				continue

			line_matches = collection_regex[collection].match(line)
			if not line_matches:
				# One of the files is truncated. Skip and go on.
				print "Invalid line: ", line
				continue
			
			row = {}

			match_groups = line_matches.groups()
			for i in range(len(match_groups)):
				field, separator, _ = fields[collection][i]

				if match_groups[i] is not None:
					# The source files are in an encoding similar or equal to IBM Code Page 850.
					value = match_groups[i].decode("cp850")
					
					value = value.strip()
					
					if separator:
						value = value.split(separator) if value != "" else []
						
						if field == "dates":
							value = [parse_date(d) for d in value]
						
					if field in ("congress", "session", "volume") and value != "":
						value = str(int(value))
						
					row[field] = value					
				else:
					row[field] = [] if separator else ""

			data.append(row)
			
	with open("csv/%s%03d.csv" % (collection, volume), "w") as csv_file:
		csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
		for line in data:
			row = []
			for ( field, separator, _ ) in fields[collection]:
				value = line[field]
				if separator: value = separator.join(value)
				row.append(value.encode("utf8"))
			csv_writer.writerow(row)

	with open("json/%s%03d.json" % (collection, volume), "w") as json_file:
		new_data = []

		for row in data:
			# Also compute the URL to view the page on the American Memory website and to
			# the direct links for the TIF and GIF images.
			record_digits = 5 if (collection, volume) in ( ('llhb', 41), ('llhb', 42) ) else 4
			row["record_number"] = int(row["image"][0:record_digits])
			row["link"] = "http://memory.loc.gov/cgi-bin/ampage?collId=%s&fileName=%03d/%s%03d.db&recNum=%d" % (
				collection,
				volume,
				collection,
				volume,
				row["record_number"] - 1,
				)
			row["large_image_url"] = "http://memory.loc.gov/ll/%s/%03d/%s/%s" % (
				collection,
				volume,
				row["image"][0:record_digits-2] + "00",
				row["image"],
				)
			row["small_image_url"] = row["large_image_url"].replace(".tif", ".gif")

			# Normalize some values.
			for field in ("congress", "session", "volume", "page"):
				if row[field] != "":
					row[field] = int(row[field])
				else:
					row[field] = None
			
			# Group the pages of documents together.
			page_fields = ('page', 'image', 'link', 'large_image_url', 'small_image_url', 'record_number')
			if row["page"] == None:
				row["pages"] = [ { } ]
				for f in page_fields:
					row["pages"][0][f] = row[f]
					del row[f]
				new_data.append(row)
			else:
				new_data[-1]["pages"].append(dict(
					(f, row[f]) for f in page_fields
				))
				
		json.dump(new_data, json_file, indent=2, separators=(',', ': '), sort_keys=True)

