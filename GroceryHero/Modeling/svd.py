from GroceryHero.models import Recipes, User
import surprise as s
import pandas as pd
# from GroceryHero import db, create_app


def recipe_svd(all_users):  # Make sure only recommend public or friend recipes
    all_history = [[item for sublist in user.history.values() for item in sublist] for user in all_users if
                   len(user.history.values())>0]  # Transaction history
    all_user_ids = [user.id for user in all_users if len(user.history.values())>0]  # Users ids
    all_items = sorted({item for sublist in all_history for item in sublist})  # Set of recipe ids
    data = [[all_user_ids[i], item, all_history[i].count(item)] for item in all_items
            for i, user_hist in enumerate(all_user_ids)]  # For each user
    data = pd.DataFrame(data, columns=['userID', 'itemID', 'rating'])  # Create dataframe
    data['rating'] = (data['rating'] - data['rating'].min()) / (data['rating'].max() - data['rating'].min())
    data = s.Dataset.load_from_df(data[['userID', 'itemID', 'rating']], s.Reader(rating_scale=(0, 1)))
    svd = s.SVD(n_factors=100, n_epochs=50)  # Initialize model
    trainset = data.build_full_trainset()  # Convert data to Trainset Object
    svd.fit(trainset)  # Train model
    rankings = {User.query.filter_by(id=user_id).first().id:  # Create rankings for each user
                sorted([[Recipes.query.filter_by(id=item).first(), svd.estimate(i, j)]
                        for j, item in enumerate(all_items)], key=lambda x: x[1], reverse=True)
                for i, user_id in enumerate(all_user_ids)}
    return rankings


# db.app = create_app()
# with db.app.app_context():
#     all_users = User.query.all()  # Get all user objects
#     rankings = recipe_svd(all_users)
#     for user in rankings:  # Convert recipe ids to their names
#         for i, item in enumerate(rankings[user]):
#             if item[0] is not None:
#                 rankings[user][i] = [item[0].id, item[0].title, item[1]]
#             else:
#                 del rankings[user][i]
    #     rankings = {}
    #     for i, user_id in enumerate(all_user_ids):
    #         username = User.query.filter_by(id=user_id).first().username
    #         rankings[username] = []
    #         for j, item in enumerate(all_items):
    #             rankings[username].append([Recipes.query.filter_by(id=item).first(), svd.estimate(i, j)])
    #             pass
    # for user in rankings:
    #     print(user, rankings[user])

    # predictions = svd.test(trainset)
    # accuracy.rmse(predictions, verbose=True)
    # users = User.query.all()
    # for user in users:
    #     hist_dict = {}
    #     today = datetime.utcnow() - timedelta(days=1)
    #     history = user.history
    #     for week in history:
    #         hist_dict[today.strftime(today.strftime('%Y-%m-%d %H:%M:%S'))] = week
    #         today = today - timedelta(days=7)
    #     user.history = hist_dict
    # db.session.commit()

    # for user in all_users:
    #     history = user.history.values()
    #     if len(history) > 0:
    #         all_history.append([item for sublist in history for item in sublist])  # Get their transaction history (recipe ids)
    #         all_user_ids.append(user.id)  # Get users ids
    # for i, user_hist in enumerate(all_user_ids):  # Create dataset
    #     for item in all_items:
    #         count = all_history[i].count(item)  # Count number of times item is in user history
    #         data.append([all_user_ids[i], item, count])
    # data = []
    # for i, user_hist in enumerate(all_user_ids):  # Create dataset
    #     for item in all_items:
    #         count = all_history[i].count(item)  # Count number of times item is in user history
    #         data.append([all_user_ids[i], item, count])
