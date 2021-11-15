import openpyxl

def writeToExcel():
    wb = openpyxl.load_workbook("templates/template_input_plateform")
    sheet = wb.active
    
    wb.save("platform_input.xlsx")