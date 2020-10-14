from random import randint, sample
import numpy as np
import pandas as pd


class Temp:
    recipes = None

    def __init__(self, recipes=recipes, name=None):
        self.recipes = recipes
        self.name = name


# def fake(recipe_num, groups):  # Creates dumb recipe chooser (in order)
#     stream = []
#     batches_num = np.ceil(recipe_num / groups)
#     containers = []
#     recipes = [x for x in range(1, recipe_num + 1)]
#     extra = recipe_num % groups
#     for i in range(1, weeks):
#         if groups <= len(recipes):  # 1 & 2
#             container = Temp()
#             container.recipes = recipes[:groups]
#             stream.append(container.recipes)
#             for x in container.recipes:
#                 recipes.remove(x)
#             containers.append(container)
#         elif len(recipes) > 0:  # 3
#             container = Temp()
#             container.recipes = list(recipes) + containers[int(i % batches_num)].recipes[:groups - len(recipes)]
#             stream.append(container.recipes)
#             containers.append(container)
#             recipes = []
#         else:
#             containers[int(i % batches_num) - 1].recipes = containers[int((i - 1) % batches_num)].recipes[-extra:] + \
#                                                            containers[int(i % batches_num)].recipes[:-extra]
#             stream.append(containers[int(i % batches_num) - 1].recipes)
#     return stream
#
#
# trials = 2000
# weeks = 50
# X = []
# for trial in range(trials):
#     recipe_num = randint(20, 50)
#     groups = randint(3, 7)
#     reverse = randint(0, 1)
#     if reverse == 1:
#         X.append(np.array(list(reversed([list(reversed(x)) for x in fake(recipe_num, groups)]))))
#     else:
#         X.append(np.array(fake(recipe_num, groups)))


# pd.to_pickle(pd.DataFrame(X), 'Seq2Seq.pickle')


weeks = 50
stream = []  # Permanent storage of recipe choices through time
preference = 8   # 80/20 randint(0,9)  # % preference for the next weeks recipes vs weeks before last
recipe_num = 21  # randint(20, 50)
groups = 7  # Number to be picked each time
cont_num = np.ceil(recipe_num / groups)  # Number of containers needed to hold all the recipes
recipes_list = [x for x in range(recipe_num)]

containers = [Temp(recipes=recipes_list, name=0)]  # Holds containers. Default container holds all recipes
cont_prob = [[x for x in range(1, 11)]]  # Index is container, value is likelihood of container being chosen
recipe_prob = {0: [x for x in containers[0].recipes]}  # Recipe's cont's index as Key, recipes as Value
offset = 0
print(0)
print(f'Cont_prob: {cont_prob}')
for i in range(1, weeks+1):  # How many elements will be in the stream list
    # if len(containers[0].recipes) < 1:
    #     cont_num = cont_num - 1
    #     containers = containers[1:]
    #     cont_prob = cont_prob[1:]
    #     del recipe_prob[0]
    #     recipe_prob = {int(i-1): k for i, k in recipe_prob.items()}
    #     offset = 1
    # print(f'Stream: {stream}')
    print(f'Iteration: {i}')
    print(f'Probs: {cont_prob}')
    if i <= cont_num:  # Make another container if more needed
        temp = Temp()  # Make container
        picks = []
        while len(picks) < groups:
            cont_roll = randint(1, 10)  # roll a container
            print(f'Roll: {cont_roll}')
            cont_choice = [index for index, probs in enumerate(cont_prob) if cont_roll in probs]  # Pick from cont_prob
            choices = recipe_prob[cont_choice[0]] if len(cont_choice) < 2 \
                else [item for sublist in [recipe_prob[stack] for stack in cont_choice] for item in sublist]
            print(f'Container {cont_choice} IDs: {choices}')
            if len(choices) < 1:  # Pick from another container if one is empty
                continue
            choice = sample(choices, 1)[0]
            picks.append(choice)
            for key in recipe_prob:  # Remove that recipe from that recipe probability group
                if choice in recipe_prob[key]:
                    recipe_prob[key].remove(choice)
                    break  # Only one instance of the recipe
        print(f'picks: {picks}')
        stream.append(picks.copy())  # User chose these recipes
        for recipe in picks:
            for container in containers:  # Recipes removed from previous owner
                if recipe in container.recipes:
                    container.recipes.remove(recipe)
                    break  # Only one instance of the recipe
        temp.recipes = picks
        recipe_prob[i] = picks
        containers.append(temp)
        print(f'Conts {[sorted(x.recipes) for x in containers]}')
        cont_prob.append([0])  # Just loaded container has 0% chance of being picked from next
        if len(containers) == 2:  # i=1
            cont_prob[0] = [x for x in range(1, 11)]  # Default has 100% chance of selection
        elif len(containers) == 3:  # i=2
            cont_prob[0] = [x for x in range(11-preference, 11)]  # Default
            cont_prob[1] = [x for x in range(1, 11-preference)]  # One after default
        elif len(containers) == 4:  # i=3
            cont_prob[1] = [x for x in range(11-preference, 11)]  # Last last picks now 80%
            cont_prob[2] = [x for x in range(1, 11-preference)]  # One after default
            merged = recipe_prob[i-3] + recipe_prob[i-2]  # Default now shares recipes with top prob
            recipe_prob[i-3] = merged
            recipe_prob[i-2] = merged
        print('___________________________________________________________________________')
    else:  # Containers have filled out recipe options
        cycle = int(i % 3) if i % 3 != 0 else 3
        temp = containers[cycle]  # Re-cycle container
        print(f'Recycle: {cycle}')
        picks = []
        while len(picks) < groups:
            cont_roll = randint(1, 10)  # roll a container
            print(f'Roll: {cont_roll}')
            cont_choice = [index for index, probs in enumerate(cont_prob) if cont_roll in probs]  # Pick from cont_prob
            choices = recipe_prob[cont_choice[0]] if len(cont_choice) < 2 \
                else [item for sublist in [recipe_prob[stack] for stack in cont_choice] for item in sublist]
            print(f'Container w/{cont_choice} {choices}')
            if len(choices) < 1:
                continue
            choice = sample(choices, 1)[0]
            picks.append(choice)
            # Remove recipe_prob values
            for key in recipe_prob:  # Remove that recipe from that recipe probability group
                if choice in recipe_prob[key]:
                    recipe_prob[key].remove(choice)
        print(f'picks: {picks}')
        stream.append(picks.copy())  # User chose these recipes
        # Remove container recipes
        for recipe in picks:
            for container in containers:  # Remove recipes from previous owner
                if recipe in container.recipes:
                    container.recipes.remove(recipe)
                    break  # Only one instance of the recipe
        containers[0].recipes = temp.recipes  # This containers old recipes go to the junk container
        temp.recipes = picks

        recipe_prob[cycle] = recipe_prob[cycle] + picks
        cont_prob.insert(1, cont_prob.pop(-1))  # Shift everything
        print(f'Conts {sorted([item for sublist in containers for item in sublist.recipes])}')
        print()

print(stream)