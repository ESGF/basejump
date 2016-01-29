from flask import request
from ndg.saml.saml2.core import AuthzDecisionQuery, Action, Issuer, Subject, NameID, SAMLVersion
from ndg.saml.saml2.binding.soap.client.authzdecisionquery import AuthzDecisionQuerySslSOAPBinding
from uuid import uuid4
from datetime import datetime


__auth_url__ = None


def configure(app_config):
    global __auth_url__
    __auth_url__ = app_config["AUTHORIZATION_SERVICE_ENDPOINT"]


def check_access(openid, url=None):
    query = AuthzDecisionQuery()
    query.id = str(uuid4())
    query.version = SAMLVersion(SAMLVersion.VERSION_20)
    query.issueInstant = datetime.utcnow()

    query.issuer = Issuer()
    query.issuer.format = Issuer.X509_SUBJECT
    query.issuer.value = "/O=Site A/CN=PEP"

    query.subject = Subject()
    query.subject.nameID = NameID()
    query.subject.nameID.format = "urn:esgf:openid"
    query.subject.nameID.value = openid

    if url is None:
        query.resource = request.url
    else:
        query.resource = url

    query.actions.append(Action())
    query.actions[-1].namespace = Action.RWEDC_NS_URI
    query.actions[-1].value = "Read"

    binding = AuthzDecisionQuerySslSOAPBinding()
    binding.clockSkewTolerance = 1.

    if __auth_url__ is None:
        raise ValueError("No AUTHORIZATION_SERVICE_ENDPOINT provided.")
    try:
        response = binding.send(query, uri=__auth_url__)
        for assertion in response.assertions:
            for statement in assertion.authzDecisionStatements:
                if statement.resource == query.resource:
                    if statement.decision == "Permit":
                        return True
                    else:
                        return False
    except:
        raise ValueError("Unable to send authorization query")
    return False
