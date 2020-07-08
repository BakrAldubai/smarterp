# Smarterp (frappe app)
This repository is under development. The aim is to improve usability of the ERPNext (and Frappe) Open Source
enterprise resource planning web platform (https://github.com/frappe/erpnext). I started working on this during the corona crisis and am looking forward
to add additional functionality as by request from others or by my own terms. The main focus of additional features
is based on dashboarding, data analysis and machine learning algorithms.

The packages that are installed with this frappe app as per requirement are sklearn, pandas and numpy. If you want to install the app, try it out, have requests of what feature could come in hand or want to collaborate please feel free to contact me.

## Content
### Included:
- Auto Assignment of Todo's for the Issues (Module: Support of ERPNext)

### Roadmap:
- Loadbalancing for the Auto Assignment based on the open ToDo's of people
- Adding NLP to the Auto Assignment
- Finding similar documents for certain doctypes
...

### Suggestions:


## Installation

Just as any other frappe app:

<code>
  bench get-app [this_repo_link] \\
  bench install-app smarterp [site-name]
</code>

## Configuration

1. Go to your ERPNext website
2. Reload (if necessary)
3. Type in search field: Smarterp Settings
4. Enter the Administrator username of your ERPNext instance
5. Enter the Administrator password
6. Enter the base url of your site (without trailing slash)
7. Click "Train Assigner"


## Contact
marius.widmann@gmail.com

## License
MIT
