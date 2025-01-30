============================
Contributing to trame-slicer
============================

#. Clone the repository using ``git clone``
#. Install pre-commit via ``pip install pre-commit``
#. Run ``pre-commit install`` to set up pre-commit hooks
#. Make changes to the code, and commit your changes to a separate branch
#. Create a fork of the repository on GitHub
#. Push your branch to your fork, and open a pull request

Testing
--------------------------------

The library testing rely on the trame-slicer test data.
To setup your testing environment :

#. Download the `trame-slicer-test-data` zip file available in this repository's release page
#. Unzip the file content to the `tests/data` folder
#. Install the test requirements using pip using the `tests/requirements.txt` file
#. Run the tests using the pytest module ``python -m pytest tests``

Interactivity
-------------

Some tests allow for interactive interaction with the views and can be activated by using the following arguments :

``python -m pytest tests --render_interactive=<interaction_time_limit_s>``

The interactivity time limit will apply to tests using a trame server in an asyncio tasks.
Interactivity for VTK render window logic will require manually closing the windows to stop the interaction.

Commit messages
---------------

trame-slicer follows trame's commit message convention to be compatible with it's CI features including the auto
semantic release.

Tips
-----

#. When first creating a new project, it is helpful to run ``pre-commit run --all-files`` to ensure all files pass the pre-commit checks.
#. A quick way to fix ``black`` issues is by installing black (``pip install black``) and running the ``black`` command at the root of your repository.
#. Sometimes, ``black`` and ``flake8`` do not agree. Add options to your ``.flake8`` file to fix these things. See the `flake8 configuration docs <https://flake8.pycqa.org/en/latest/user/configuration.html>`_ for more details.
#. A quick way to fix ``codespell`` issues is by installing codespell (``pip install codespell``) and running the ``codespell -w`` command at the root of your directory.
#. The `.codespellrc file <https://github.com/codespell-project/codespell#using-a-config-file>`_ can be used fix any other codespell issues, such as ignoring certain files, directories, words, or regular expressions.
