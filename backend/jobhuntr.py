from flask import request, Blueprint, Response
from mongoengine import *
from bson.objectid import ObjectId
import json

bp = Blueprint("jobhuntr", __name__, url_prefix="/jobhuntr")

connect("jobs")

@bp.route("/opportunities", methods=["GET", "POST", "PUT", "DELETE"])
def opportunity():
    if request.method == "GET":
        username = request.args.get("username")
        opportunities = Opportunity.objects(applicant=username)
        processes = [{ 'id': str(opportunity.id), 'company': opportunity.company, 'position': opportunity.position, 'processes': [{ "date": process.date, "document": process.document.fetch().get_dict_representation(), "type": process.document_type } for process in opportunity.processes]} for opportunity in opportunities]
        return json.dumps(processes)

    elif request.method == "POST":
        request_json = request.get_json()
        data = request_json["data"]

        applicant = data.get("applicant")
        company = data.get("company")
        position = data.get("position")
       
        error = None
        if not applicant:
            error = "applicant must be defined"
        elif not company:
            error = "company must be defined"
        elif not position:
            error = "position must be defined"

        if error is None:
            # create opportunity
            opportunity = Opportunity(applicant=applicant, company=company, position=position)
            opportunity.save()

            return 'successfully created opportunity'

        return Response(error, 500)

    elif request.method == "PUT":
        request_json = request.get_json()
        opportunity_id = request_json["id"]
        data = request_json["data"]

        error = None
        if not opportunity_id:
            error = "opportunity id must be defined"
        
        if error is None:
            # check if there needs to be changes to opportunity and updates it
            opportunity = Opportunity.objects.get(pk=opportunity_id)
            for key in opportunity:
                if data.get(key) and data[key] != opportunity[key]:
                    opportunity[key] = data[key]
            opportunity.save()
            return 'successfully updated opportunity'
        
        return Response(error, 500)

    elif request.method == "DELETE":
        request_json = request.get_json()
        opportunity_id = request_json["id"]

        error = None
        if not opportunity_id:
            error = "opportunity id must be defined"

        if error is None:
            # query Opportunity and delete all associated processes
            opportunity = Opportunity.objects.get(pk=opportunity_id)
            for process in opportunity.processes:
                process.document.fetch().delete()
            opportunity.delete()
            return "opportunity and all processes have been deleted"

        return Request(error, 500)

    return 'you can only create, delete, and query opportunities'


@bp.route("/applications", methods=["POST", "DELETE"])
def apply():
    if request.method == "POST":
        request_json = request.get_json()
        data = request_json["data"]

        date = data.get("date")
        opportunity_id = data.get("opportunity_id")
        status = data.get("status")

        error = None
        if not date:
            error = "date is required"
        elif not opportunity_id:
            error = "opportunity id is required"
        elif not status:
            error = "status is required"

        if error is None:
            # create application
            application = Application(status=status)
            application.save()
            # create new process
            opportunity = Opportunity.objects.get(pk=opportunity_id)
            opportunity.processes.append(Process(date=date, document=application, document_type="application", parent=opportunity))
            opportunity.save()
            # update application parent
            application.parent = opportunity
            application.save()
            return 'successfully created application'

        return Response(error, 500)

    elif request.method == "DELETE":
        request_json = request.get_json()
        application_id = request_json.get("id")

        error = None
        if not application_id:
            error = "application id is required"

        if error is None:
            application = Application.objects.get(pk=application_id)
            opportunity = application.parent.fetch()
            for process in opportunity.processes:
                if process.document == application:
                    opportunity.processes.remove(process)
                    opportunity.save()
                    application.delete()
                    return "Successfully deleted application and associated process"
            return Response("Unable to find associated process", 500)

        return Response(error, 500)

    else:
        return "you can only create and delete applications at this time."

@bp.route("/interviews", methods=["POST", "DELETE"])
def interview():
    if request.method == "POST":
        request_json = request.get_json()
        data = request_json["data"]
        
        date = data.get("date")
        interviewer = data.get("interviewer")
        location = data.get("location")
        opportunity_id = data.get("opportunity_id")
        notes = data.get("notes")
        url = data.get("url")

        error = None
        if not date:
            error = "date is required"
        if not opportunity_id:
            error = "opportunity id is required"

        if error is None:
            interview = Interview(interviewer, location, notes, url)
            interview.save()
            opportunity = Opportunity.objects.get(pk=opportunity_id)
            opportunity.processes.append(Process(date, interview, "interview", opportunity))
            opportunity.save()
            interview.parent = opportunity
            interview.save()
            return("successfully created interview")

        return Response(error, 500)

    elif request.method == "DELETE":
        request_json = request.get_json()
        interview_id = request_json.get("id")

        error = None
        if not interview_id:
            error = "interview id is required"

        if error is None:
            interview = Interview.objects.get(pk=interview_id)
            opportunity = interview.parent.fetch()
            for process in opportunity.processes:
                if process.document == interview:
                    opportunity.processes.remove(process)
                    opportunity.save()
                    interview.delete()
                    return "Successfully deleted interivew and associated process"
            return Response("Unable to find associated process", 500)

        return Response(error, 500)

    else:
        return "you can only create and delete interviews at this time."
        
class Application(Document):
    parent = GenericLazyReferenceField()
    status = StringField(required=True)

    def __str__(self):
        return str({"id": self.id, "status": self.status})

    def get_dict_representation(self):
        return {'id': str(self.id), 'status': self.status}

class Interview(Document):
    interviewer = StringField()
    location = StringField()
    notes = StringField()
    parent = GenericLazyReferenceField()
    url = StringField()

    def get_dict_representation(self):
        return { 'id': str(self.id), 'interviewer': self.interviewer, 'location': self.location, 'notes': self.notes, 'url': self.url }

class Process(EmbeddedDocument):
    date = StringField(required=True)
    document = GenericLazyReferenceField(required=True)
    document_type = StringField(required=True)
    parent = GenericLazyReferenceField()

class Opportunity(Document):
    applicant = StringField(required=True)
    company = StringField(required=True)
    description = StringField()
    position = StringField(required=True)
    processes = EmbeddedDocumentListField(document_type=Process)
