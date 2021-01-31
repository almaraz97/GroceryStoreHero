# import csv
from GroceryHero.Main.utils import getUserRecipeHistory
from GroceryHero.models import Recipes, User
from apyori import apriori
from GroceryHero import db, create_app


# dictionary with transaction number as key and list(set(item_ids)) as value
# def read_data(file_loc='GroceryStoreDataSet.csv'):
#     trans = dict()
#     with open(file_loc) as f:
#         filedata = csv.reader(f, delimiter=',')
#         count = 0
#         for line in filedata:
#             count += 1
#             trans[count] = list(set(line))
#     return trans  # Probably not necessary for me

# def frequence(items_lst, trans, check=False):
#     items_counts = {}
#     for i in items_lst:
#         temp_i = {i}
#         if check:
#             temp_i = set(i)
#         for j in trans.items():
#             if temp_i.issubset(set(j[1])):
#                 if i in items_counts:
#                     items_counts[i] += 1
#                 else:
#                     items_counts[i] = 1
#     return items_counts
#
#
# def support(items_counts, trans):
#     support = {}
#     total_trans = len(trans)
#     for i in items_counts:
#         support[i] = items_counts[i] / total_trans
#     return support
#
#
# def association_rules(items_grater_then_min_support):
#     rules = []
#     dict_rules = {}
#     for i in items_grater_then_min_support:
#         dict_rules = {}
#         if type(i) != type(str()):
#             i = list(i)
#             temp_i = i[:]
#             for j in range(len(i)):
#                 k = temp_i[j]
#                 del temp_i[j]
#                 dict_rules[k] = temp_i
#                 temp_i = i[:]
#         rules.append(dict_rules)
#     temp = []
#     for i in rules:
#         for j in i.items():
#             if type(j[1]) != type(str()):
#                 temp.append({tuple(j[1])[0]: j[0]})
#             else:
#                 temp.append({j[1]: j[0]})
#     rules.extend(temp)
#     return rules
#
#
# def confidence(associations, d, min_confidence):
#     ans = {}
#     for i in associations:
#         for j in i.items():
#             if type(j[0]) == type(str()):
#                 left = {j[0]}
#             else:
#                 left = set(j[0])
#             if type(j[1]) == type(str()):
#                 right = {j[1]}
#             else:
#                 right = set(j[1])
#             for k in d:
#                 if type(k) != type(str()):
#                     if left.union(right) - set(k) == set():
#                         up = d[k]
#                     if len(right) == len(set(k)) and right - set(k) == set():
#                         down = d[k]
#                 else:
#                     if len(right) >= len({k}):
#                         if right - {k} == set():
#                             down = d[k]
#                     elif len(right) <= len({k}):
#                         if {k} - right == set():
#                             down = d[k]
#             if up / down >= min_confidence:
#                 ans[tuple(left)[0]] = right, up / down, up, down
#     return ans
#
#
# def main(min_support, min_confidence, file_loc):
#     print("Hello")
#     trans = current_user.history  # read_data()
#     # trans = current_user.history.values()  # todo dictionary conversion
#     number_of_trans = [len(i) for i in trans.values()]  # List of transaction lengths
#     items_lst = set()
#     itemcount_track = []
#
#     for i in trans.values():
#         for j in i:
#             items_lst.add(j)
#
#     store_item_lst = list(items_lst)[:]
#     items_grater_then_min_support = list()
#     items_counts = frequence(items_lst, trans)
#     itemcount_track.append(items_counts)
#     items_grater_then_min_support.append(
#         {j[0]: j[1] for j in support(items_counts, trans).items() if j[1] > min_support})
#
#     for i in range(2, max(number_of_trans) + 1):
#         item_list = combinations(items_lst, i)
#         items_counts = frequence(item_list, trans, check=True)
#         itemcount_track.append(items_counts)
#         if list({j[0]: j[1] for j in support(items_counts, trans).items() if j[1] > min_support}.keys()) != []:
#             items_grater_then_min_support.append(
#                 {j[0]: j[1] for j in support(items_counts, trans).items() if j[1] > min_support})
#
#     d = {}
#     {d.update(i) for i in itemcount_track}
#     associations = association_rules(items_grater_then_min_support[len(items_grater_then_min_support) - 1])
#     associations_greater_than_confidence = confidence(associations, d, min_confidence)
#     return associations_greater_than_confidence


# main(0.01, 0.7, 'GroceryStoreDataSet.csv')


# def apriori_test(user, min_support=None, harmony=False, includes=None):
#     recipes = []
#     for week in user.history:
#         # for week in user.history.values():
#         #     temp = [recipe.title for recipe in
#         #     [Recipes.query.filter_by(id=item).first() for item in week for week in user.history.values()]]
#         temp = []
#         for item in week:
#             recipe = Recipes.query.filter_by(id=item).first()
#             if recipe is not None:
#                 temp.append(recipe.title)
#         if len(temp) > 0:
#             recipes.append(temp)
#     # recipes = [temp for temp in []]
#     min_support = 2/len(recipes) if min_support is None else min_support
#     if harmony:
#         aprioris = apriori(recipes, min_support=1e-8, min_lift=1e-8)
#         if includes is not None:
#             aprioris = [x for x in aprioris if all(y in x.items for y in includes)]
#     else:
#         aprioris = apriori(recipes, min_support=min_support, min_lift=1.1)
#         aprioris = list(aprioris)
#     return aprioris


db.app = create_app()
with db.app.app_context():
    user = User.query.all()[0]
    recipes = []
    includes = [84]
    history = getUserRecipeHistory(user)

    includes = [x.title for x in Recipes.query.filter(Recipes.id.in_(includes)).all()]
    aprioris = list(apriori(history, min_support=1e-8, min_lift=1e-8))
    deletes = []
    for i, x in enumerate(aprioris):
        if includes != x.items:
            deletes.append(i)
        if not all(y in x.items for y in includes) or len(x.items) < 2:
            deletes.append(i)
    deletes = sorted(deletes, reverse=True)
    for d in deletes:
        del aprioris[d]
    aprioris = [x for x in aprioris if all(y in x.items for y in includes)]