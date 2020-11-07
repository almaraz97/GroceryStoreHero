from GroceryHero import create_app
import os


app = create_app()

server = True if os.environ.get('SERVER') == 'True' else False

if __name__ == '__main__':
    app.run(debug=server)
