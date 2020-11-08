from GroceryHero import create_app
import os


app = create_app()

server = False if os.environ.get('SERVER') == 'True' else True

if __name__ == '__main__':
    app.run(debug=server)
