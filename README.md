# Item-Catalog


Introduction :
1. Application provides a list of restaurants and their menus.

2. Google is used for authentication and authorisation.

3. A local permission system has been implemented to keep the users from changing other user's data.

4. If user is not logged in then he/she can only view restaurants and their menus.

5. A user has to be logged in to create, edit and delete restaurants and menu Items.

6. In case user is not logged in and still tries to edit, create or delete he/she is automatically redirected to login page.


PreRequisites :
1. vagrant VM

2. Python 2.7

3. Flask 0.12.2

4. SQLAlchemy 1.1.10(which is already installed in case of vagrant)


Setup : 
1. Install Vagrant and VirtualBox.

2. Download or Clone fullstack-nanodegree-vm repository.

3. Open the directory that contains the project and launch vagrant VM.

4. Run the commands 'vagrant up', 'vagrant ssh', 'cd /vagrant'.
5. Load the database by running 'python database_setup.py'.

6. Run command 'python lotsofusers.py'.

7. Run command 'python final_project.py'.

8. Open 'localhost:8000/' or 'localhost:8000/restaurants' to test the application


Special Thanks : 
This complete project is based on udacity videos and codes from videos and instructor notes.
