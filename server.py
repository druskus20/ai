from flask import Flask, flash, render_template, request, redirect
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

IMAGE_UPLOAD_FOLDER = Path("static/images/")


def init_image_upload_folder():
    if not IMAGE_UPLOAD_FOLDER.exists():
        os.makedirs(IMAGE_UPLOAD_FOLDER)


# Init a db if it doesnt exist
def init_db():
    conn = sqlite3.connect("inventory.db")  # <-- file next to server.py
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  path TEXT NOT NULL,
                  item_id INTEGER NOT NULL,
                  FOREIGN KEY(item_id) REFERENCES items(id))""")
    conn.commit()
    conn.close()


@app.route("/item/<int:item_id>", methods=["GET"])
def item_detail(item_id):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("SELECT id, name FROM items WHERE id = ?", (item_id,))
    item = c.fetchone()
    if item is None:
        flash("Item not found!", "error")
        return redirect("/")

    item_id = item[0]
    item_name = item[1]

    c.execute("SELECT path FROM images WHERE item_id = ?", (item_id,))
    images = c.fetchall()
    images = [img[0] for img in images]  # Extract paths from tuples
    conn.close()

    ## Render the template with the `item` and its `images`
    return render_template(
        "item.html", item_id=item_id, item_name=item_name, images=images
    )


@app.route("/edit/<int:item_id>", methods=["POST"])
def edit(item_id):
    new_name = request.form["item_name"]

    if new_name:
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
        conn.commit()
        conn.close()
    else:
        flash("New name is expected!", "error")

    return redirect(f"/item/{item_id}")


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()

    # Delete associated images from filesystem
    c.execute("SELECT path FROM images WHERE item_id = ?", (item_id,))
    images = c.fetchall()
    for img in images:
        image_path = img[0]
        if Path(image_path).exists():
            os.remove(image_path)

    # Delete images from DB
    c.execute("DELETE FROM images WHERE item_id = ?", (item_id,))

    # Delete the item
    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return redirect("/")


# Add a new item
@app.route("/add", methods=["POST"])
def add():
    item_name = request.form["item_name"]
    item_image = request.files["item_image"]

    if item_name:
        ## Insert the item
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("INSERT INTO items (name) VALUES (?)", (item_name,))
        conn.commit()
        conn.close()
    else:
        flash("Item name is expected!", "error")
        return redirect("/")

    if item_image:
        # Insert the image path into the DB
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        # Get the id of the last inserted item
        c.execute(
            "SELECT id FROM items WHERE name = ? ORDER BY id DESC LIMIT 1", (item_name,)
        )
        item_id = c.fetchone()[0]
        if not item_id:
            flash("Item not found for image upload!", "error")
            return redirect("/")

        image_filename = f"{item_id}_{item_image.filename}"

        # Create /item_id folder if not exists
        image_path = IMAGE_UPLOAD_FOLDER.joinpath(str(item_id), image_filename)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        # Add an entry in the images table
        c.execute(
            "INSERT INTO images (path, item_id) VALUES (?, ?)",
            (str(image_path), item_id),
        )
        conn.commit()
        conn.close()

        # Save the image in the filesystem
        item_image.save(image_path)

    return redirect("/")


# Index
@app.route("/", methods=["GET"])
def index():
    ## List items from DB
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("SELECT * FROM items ORDER BY id DESC")
    items = c.fetchall()
    conn.close()

    ## Render the template with the `items`
    return render_template("index.html", items=items)


# What runs when you run `python3 server.py`
# (python is stupid)
if __name__ == "__main__":
    init_db()
    init_image_upload_folder()
    app.run(debug=True)
