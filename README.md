# Smarterp
This repository is under development. The aim is to improve usability of the ERPNext (and Frappe) Open Source
enterprise resource planning web platform (https://github.com/frappe/erpnext). I started working on this during the corona crisis and am looking forward
to add additional functionality as by request from others or by my own terms. The main focus of additional features
is based on dashboarding, data analysis and machine learning algorithms.

The packages that are installed with this frappe app as per requirement are sklearn, pandas and numpy. If you want to install the app, try it out, have requests of what feature could come in hand or want to collaborate please feel free to contact me.

## Content
### Included:
- Assignment Assistant for the Issues (Module: Support of ERPNext)

### Roadmap:
- Add task scheduler
- Loadbalancing for the Auto Assignment based on the open ToDo's of people
- Adding NLP to the Auto Assignment
- Finding similar documents for certain doctypes
...

### Auto Assignemnt
The model is trained with the existing data. You should have at least ~ 100 issues in your erp.
Based on doctypes:
- Todos
- Issues
- Timesheets
- Projects
- Customers
- Employees
- Contacts

All of these should contain documents already. The more the better. If your testing or development environment does not support
live data, you can in the settings use the login information for a production environment. It will pull data from there in a one-way fashion. It will not delete, modify or otherwise compromise the production environment. Please also check with your data privacy. The data will be downloaded as tables onto the system where you install the app. It will be located under /sites/sitename/assigner
You can always delte this folder and all data is removed.

## Installation

Just as any other frappe app:

<code>
  bench get-app [this_repo_link]  
  
  bench install-app smarterp [site-name]
</code>

## Configuration

1. Go to your ERPNext website
2. Reload (if necessary)
3. Type in search field: Smarterp Settings
4. Enter the Administrator username of your ERPNext instance (use a production instance, it will pull data from there (one-way) )
5. Enter the Administrator password (use production instance)
6. Enter the base url of your site (without trailing slash / use production instance)
7. Click "Train Assigner" 
(Takes about 10 minutes, Reload the page and the Last Trained field will be set after training has finished)

8. For better performance the training should be done once a day or every second day (Task scheduler to automate it is under way).

![alt text](https://github.com/canlann/smarterp/blob/master/readme-settings.png)

## Contact
marius.widmann@gmail.com

## License
MIT
