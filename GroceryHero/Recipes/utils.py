from GroceryHero.Recipes.forms import Measurements


def parse_ingredients(ingredients):
    measures = Measurements.Measures
    extras = ['cup', 'tablespoon', 'teaspoon', 'fluid ounce']
    convert = {'Unit': 'Unit', 'Package': 'Package', 'Can': 'Can', 'Bottle': 'Bottle', 'Jar': 'Jar', 'US Cup': 'US Cup',
               'US Tablespoon': 'US Tablespoon', 'US Teaspoon': 'US Teaspoon', 'US Fluid Ounce': 'US Fluid Ounce',
               'Ounce': 'Ounce', 'Pound': 'Pound', 'Milligram': 'Milligram', 'Gram': 'Gram', 'Kilogram': 'Kilogram',
               'Milliliter': 'Milliliter', 'Liter': 'Liter', 'cup':'US Cup', 'tablespoon': 'US Tablespoon',
               'teaspoon': 'US Teaspoon', 'fluid ounce': 'US Fluid Ounce'}
    # convert = {(k if all([x not in k for x in extras]) else extras[extras.index(k)]): k for k in measures}
    measures = measures + extras
    quantity = []
    ings = []
    for i, ingredient in enumerate(ingredients):
        temp = ''  # New string for ingredients list, gets chars appended as it goes through
        nums = ''
        cons = 0
        for j, char in enumerate(ingredient):
            try:
                if isinstance(float(char), float):  # Need to be able to parse fractions and decimals
                    nums = nums + char
                    cons = j
            except ValueError:
                if len(nums) > 0:  # Number may have ended ended
                    if char == '/' and (cons+1) == j:  # If there is a number before the / add it
                        nums = nums + char
                    else:
                        quantity.append([nums])
                        temp = temp + ingredient[j:]  # A number is found, add the rest of the string
                        break
                elif j == len(ingredient)-1:  # No quantity found
                    quantity.append([])
                else:
                    temp = temp + char
        ings.append(' '.join([x.strip() for x in temp.split(' ') if x != ' ' and x != '']))
        found = False
        for measure in measures:
            if ' '+measure.lower()+'s ' in ings[i]:
                ings[i] = ings[i].replace(' '+measure.lower()+'s ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            if ' '+measure.lower()+' ' in ings[i]:
                ings[i] = ings[i].replace(' '+measure.lower()+' ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            length = len(measure)
            if ings[i][:length+1] == measure+' ':  # Unit is the first part of the string
                ings[i] = ings[i].replace(measure.lower() + ' ', '')
                quantity[i].append(convert[measure])
                found = True
                break
            if ings[i][:length+2] == measure+'s ':  # Unit is the first part of the string
                ings[i] = ings[i].replace(measure.lower() + 's ', '')
                quantity[i].append(convert[measure])
                found = True
                break
        if not found:
            if len(quantity[i]) < 1:
                quantity[i].append('1')
            quantity[i].append('Unit')
        ings[i] = ings[i].strip()
    print(ings)
    return ings, quantity