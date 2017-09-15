import csv
import sys

#this analyzer calculates how a user performs after playing REFERENCE
with open("full-process.csv") as csvfile:

    readCSV = csv.reader(csvfile, delimiter=',')

    Names = []
    Puzzles = []
    Points = []
    ticker = False
    total = 0

    for row in readCSV:
        if ticker is True:
            total += (str(row[5]).count('C') - points)
            ticker = False;

        if row[2] == "REFERENCE":
            points = str(row[5]).count('C')
            ticker = True

        if row[2] == "END":
            Names.append(row[0])
            Puzzles.append(row[1])
            Points.append(total)
            total = 0

with open('feedbackAnalysis.csv', 'w', newline='') as result:
    try:
        writeCSV = csv.writer(result)
        writeCSV.writerow(('Codename', 'Puzzle', 'Feedback'))
        for i in range(0, len(Names)):
            writeCSV.writerow((Names[i], Puzzles[i], Points[i]))
    finally:
        result.close()

print("done")
