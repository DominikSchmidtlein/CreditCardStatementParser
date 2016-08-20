import sys
import re
import os
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter#process_pdf
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from cStringIO import StringIO

match_date = r"[A-Z]{3}\d{2}"
date_group = r"(?P<date>%s)" % (match_date)
location_group = r"(?P<location>.*?)"
price_group = r"(?P<price>\-?\$\d+\.\d{2})"
match_transaction = r"%s%s%s\d*%s" % (date_group, match_date, location_group, price_group)
match_month_name = r"(?<=STATEMENTFROM)[A-Z]{3}\d{2}(,\d{4})?TO(?P<month>[A-Z]{3})\d{2},(?P<year>\d{4})"
match_new_balance = r"(?<=NEWBALANCE\$)\d+\.\d{2}"
match_previous_balance = r"(?<=PREVIOUSSTATEMENTBALANCE\$)\d+\.\d{2}"

months = []
locations = {}
categories = []

def parse_locations():
	open_file = None
	try:
		open_file = open("locations.txt")
	except IOError:
		return
	line = open_file.readline()
	while line:
		splits = line.split()
		locations[splits[0]] = splits[1]
		if splits[1] != "payment" and splits[1] not in categories:
			categories.append(splits[1])
		line = open_file.readline()
	open_file.close()

def parse_credit_statement(path):
	for filename in os.listdir(path):
		if filename.endswith('.pdf'):
			print filename
			text = parse_pdf(filename)
			date, prev, new = extract_headers(text)
			transactions = extract_transactions(text)
			months.append({
				'date': date,
				'previous': prev,
				'new': new,
				'transactions': transactions,
			})
			assert abs(new - calculate_total(transactions, True) - prev) < 0.1 

# returns text
def parse_pdf(filename):
	# PDFMiner boilerplate
	rsrcmgr = PDFResourceManager()
	sio = StringIO()
	codec = 'utf-8'
	laparams = LAParams()
	device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
	interpreter = PDFPageInterpreter(rsrcmgr, device)
	# Extract text
	fp = file(filename, 'rb')
	for page in PDFPage.get_pages(fp):
	    interpreter.process_page(page)
	fp.close()
	# Get text from StringIO
	text = sio.getvalue()
	# Cleanup
	device.close()
	sio.close()
	return text

def extract_headers(text):
	match = re.search(match_month_name, text)
	month_name = "%s %s" % (match.group('month'), match.group('year'))
	new_balance = float(re.search(match_new_balance, text).group(0))
	previous_balance = float(re.search(match_previous_balance, text).group(0))
	return (month_name, previous_balance, new_balance)

def extract_transactions(text):
	transactions = []
	for match in re.finditer(match_transaction, text):
		transaction = {
			'date': match.group('date'),
			'location': match.group('location'),
			'price': float(match.group('price').replace('$', '')),
		}
		transactions.append(transaction)
	return transactions

def check_locations():
	locations_string = ""
	for month in months:
		for transaction in month['transactions']:
			if transaction['location'] not in locations.keys():
				locations[transaction['location']] = ""
				locations_string += transaction['location'] + "\n"
	if locations_string:
		open_file = open("locations.txt", 'a')
		open_file.write(locations_string)
		open_file.close()
		print "Locations missing!!!"
		sys.exit(1)

def categorize_transactions():
	for month in months:
		m_categories = {}
		for transaction in month['transactions']:
			category = locations[transaction['location']]
			if category not in m_categories.keys():
				m_categories[category] = 0
			m_categories[category] += transaction['price']
		month['categories'] = m_categories

def months_to_string():
	string = "Month,Total,"
	for category in categories:
		string += category + ','
	string += '\n'
	for month in months:
		string += month['date'] + ','
		string += str(month['total']) + ','
		for cat in categories:
			if cat in month['categories'].keys():
				string += str(month['categories'][cat])
			else:
				string += '0'
			string += ','
		string += '\n'	
	return string

def calculate_totals():
	for month in months:
		total = calculate_total(month['transactions'], False)
		month['total'] = total

def calculate_total(transactions, include_payments):
	total = 0
	for transaction in transactions:
		if include_payments or locations[transaction['location']] != "payment":
			total += transaction['price']
	return total

def print_months():
	print '['
	for month in months:
		print '{'
		print 'date: %s' % (month['date'])
		print 'previous: %f' % (month['previous'])
		print 'new: %f' % (month['new'])
		print '},'
	print ']'
		
def main():
	path = sys.argv[1]

	parse_locations()
	parse_credit_statement(path)
	check_locations()

	calculate_totals()

	# categorize
	categorize_transactions()
	open_file = open("output.csv", 'w')
	open_file.write(months_to_string())
	open_file.close()

if __name__ == '__main__':
	main()

