def accumu(lis):
    total = 0
    for v in lis:
        total += v
        yield total

def getSubRow(sheet, row, start_col, length):
    return [sheet.cell(row, start_col + t).value for t in range(length)]