import csv
import sys

csv.field_size_limit(sys.maxsize)

filename = "overall_checked_claims.csv"

complete_lines = 0


with open(filename, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) in (13, 12):
            complete_lines += 1

print(f"Number of complete lines (11 or 12 fields): {complete_lines}")