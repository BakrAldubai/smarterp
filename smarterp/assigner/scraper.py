import requests
import pandas as pd
import datetime
import csv

class Scraper:
    def __init__(self, path):
        self.session = None
        self.issues = None
        self.todos = None
        self.contacts = None
        self.timesheets = None
        self.customers = None
        self.projects = None
        self.employees = None
        self.filename_prefix = path + datetime.datetime.now().strftime("%d.%m.%Y")

        
        self.url = None

    def auth(self,username,password):
        #Input Adminpassword
        if(password == None):
            username = input("Enter Administrator Username:")
            pwd = input("Enter Administrator Password:")
        else:
            pwd = password

        #Open Session for olderp
        s = requests.Session()
        j = {}
        j["usr"] = username
        j["pwd"] = pwd
        #print("Logging in on olderp with: " + str(j))
        r = s.post(self.url + "/api/method/login",j)
        print("Login ERP: " + str(r.status_code))
        
        return s
    
    def scrape(self,username, password, baseurl):
        self.url = baseurl
        self.session = self.auth(username, password)
        
        #Issues
        issues = self.getIssueList()
        self.issues = pd.DataFrame.from_records(issues)

        #Todos
        todos = self.getTodoList()
        self.todos = pd.DataFrame.from_records(todos)

        #Contacts
        contacts, keys = self.getContacts()
        self.contacts = pd.DataFrame(contacts, columns=keys)

        #Timesheets
        timesheets = self.getTimesheets()
        self.timesheets = pd.DataFrame.from_records(timesheets)


        #Customers
        customers = self.getCustomerList()
        self.customers = pd.DataFrame.from_records(customers)

        #Projects
        projects = self.getProjectList()
        self.projects = pd.DataFrame.from_records(projects)

        #Employees
        employees = self.getEmployeesList()
        self.employees = pd.DataFrame.from_records(employees)

    def save(self):
        self.issues.to_csv(self.filename_prefix + '_issues.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.todos.to_csv(self.filename_prefix + '_todos.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.contacts.to_csv(self.filename_prefix + '_contacts.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.timesheets.to_csv(self.filename_prefix + '_timesheets.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.customers.to_csv(self.filename_prefix + '_customers.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.projects.to_csv(self.filename_prefix + '_projects.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)
        self.employees.to_csv(self.filename_prefix + '_employees.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"', index=False)

    def load(self):
        self.issues = pd.read_csv(self.filename_prefix + '_issues.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.todos = pd.read_csv(self.filename_prefix + '_todos.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.contacts = pd.read_csv(self.filename_prefix + '_contacts.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.timesheets = pd.read_csv(self.filename_prefix + '_timesheets.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.customers = pd.read_csv(self.filename_prefix + '_customers.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.projects = pd.read_csv(self.filename_prefix + '_projects.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')
        self.employees = pd.read_csv(self.filename_prefix + '_employees.csv', sep=";", quoting=csv.QUOTE_ALL, quotechar='"')

    def getIssueList(self):
        r = self.session.get(self.url + '/api/resource/Issue?limit_page_length=20000&fields=["name","subject","description","owner","creation","modified","modified_by","customer","raised_by","status","priority","agreement_fulfilled","contact","project","opening_date","opening_time","email_account"]',verify=False)
        print("Download Issue List: " + str(r.status_code))
        j = r.json()
        issues = j["data"]

        return issues

    def getTodoList(self):
        r = self.session.get(self.url + '/api/resource/ToDo?limit_page_length=20000&fields=["name","owner","status","reference_type","reference_name","assigned_by","creation","modified"]&filters=[["reference_type","=","Issue"]]')
        print("Download Todo List: " + str(r.status_code))
        j = r.json()
        todos = j["data"]

        return todos

    def assign(self,issues, todos):
        assigned = []
        for todo in todos:
            for issue in issues:
                assignment = issue.copy()
                if(todo["reference_name"] == issue["name"]):
                    for key, value in todo.items():
                        assignment["todo_" + key] = value
                    assigned.append(assignment)
                    break
        return assigned

    def getContacts(self):

        r = self.session.get(self.url + '/api/resource/Contact?fields=["name"]&limit_page_length=20000')
        print("Download Contact List: " + str(r.status_code))
        j = r.json()
        contacts_list = j["data"]
        print("Downloaded Contact List: " + str(len(contacts_list)) + " Contacts.")

        contacts = []
        for instance in contacts_list:
            contact = {}
            r = self.session.get(self.url + '/api/resource/Contact/' + instance["name"])
            j = r.json()
            data = j["data"]
            select_fields = ["name","first_name", "last_name", "email_id", "phone", "mobile_no"]
            for field in select_fields:
                if(field in data.keys()):
                    contact[field] = data[field]
                else:
                    contact[field] = None
            
            phone_nos = data["phone_nos"]
            contact["phone_nos"] = ""
            for no in phone_nos:
                contact["phone_nos"] += no["phone"] + "; "
            if len(phone_nos) == 0:
                contact["phone_nos"] = None

            links = data["links"]
            found_customer = False
            for link in links:
                if(link["link_doctype"] == "Customer" and not found_customer):
                    contact["customer"] = link["link_name"]
                    contact["customer_title"] = link["link_title"]
                    found_customer = True
            if(not found_customer):
                contact["customer"] = None
                contact["customer_title"] = None
            
            email_ids = data["email_ids"]
            for mail in email_ids:
                contact["email_ids"] = mail["email_id"]
            if len(email_ids) == 0:
                contact["email_ids"] = None
            
            contacts.append(contact)
        keys = ["name","first_name", "last_name", "email_id", "phone", "mobile_no", "phone_nos", "customer", "customer_title","email_ids"]

        return contacts, keys

    def getTimesheets(self):
        r = self.session.get(self.url + '/api/resource/Timesheet?fields=["name"]&limit_page_length=20000')
        print("Download Timesheet List: " + str(r.status_code))
        j = r.json()
        tsl = j["data"]
        for ts in tsl:
            r = self.session.get(self.url + '/api/resource/Timesheet/' + ts["name"])
            j = r.json()
            data = j["data"]
            ts["owner"] = data["owner"]
            #ts["creation"] = data["creation"]
            ts["employee"] = data["employee"]  if "employee" in data else None
            ts["employee_name"] =  data["employee_name"] if "employee_name" in data else None
            ts["start_date"] = data["start_date"]
            ts["total_hours"] = data["total_hours"]
            ts["total_billed_hours"] = data["total_billed_hours"]
            if("issue" in data):
                ts["issue"] = data["issue"]
            else:
                ts["issue"] = None
            for log in data["time_logs"]:
                if('project' in log):
                    ts["project"] = log["project"]
                else:
                    ts["project"] = None
            if("note" in data):
                ts["note"] = data["note"]
            else:
                ts["note"] = None
        return tsl

    def getCustomerList(self):
        r = self.session.get(self.url + '/api/resource/Customer?fields=["name","customer_name"]&limit_page_length=20000')
        print("Download Customer List: " + str(r.status_code))
        j = r.json()
        csl = j["data"]
        return csl

    def getProjectList(self):
        r = self.session.get(self.url + '/api/resource/Project?fields=["name","customer","customer_name"]&limit_page_length=20000')
        print("Download Project List: " + str(r.status_code))
        j = r.json()
        psl = j["data"]
        return psl

    def getEmployeesList(self):
        r = self.session.get(self.url + '/api/resource/Employee?fields=[%22name%22,%22user_id%22]&limit_page_length=20000')
        print("Download Employees List: " + str(r.status_code))
        j = r.json()
        esl = j["data"]
        return esl