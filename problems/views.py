import os
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.move import file_move_safe
from django.contrib import messages
from django.contrib.auth.models import User

from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.utils.translation import ugettext as _

from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import View

from base.util import convert_files_to_single_pdf, get_uploaded_filepath, remove_accents
from competitions.models import Series
from competitions.views import CurrentSiteCompetitionMixin

from problems.models import Problem, UserSolution
from problems.forms import UserSolutionForm, ImportCorrectedSolutionsForm
from roots import settings

from profiles.models import UserProfile



class ProblemListView(ListView):

    model = Problem
    context_object_name = 'problems'


class ProblemDetailView(DetailView):

    model = Problem
    context_object_name = 'problem'


class UserSolutionEvaluationView(DetailView):

    model = UserSolution
    context_object_name = 'usersolution'
    template_name = 'problems/solution_evaluation.html'


class UserSolutionSubmissionView(View):

    form_class = UserSolutionForm

    def get(self, request, *args, **kwargs):
        return redirect('competitions_season_detail_latest')

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            data = dict(
                user=request.user,
                problem=Problem.objects.get(pk=form.cleaned_data['problem'])
            )

            try:
                submission =  UserSolution.objects.get(**data)
            except UserSolution.DoesNotExist:
                submission = UserSolution(**data)

            # do not save and return if user does not have filled profile
            try:
                userprofile = UserProfile.objects.get(user = data['user'])
                required_attrs = ('school', 'school_class', 'classlevel')

                for attr in required_attrs:
                    if (getattr(userprofile, attr, None) is None):
                        raise ValidationError(_('incomplete_profile'))

            except (ValidationError, UserProfile.DoesNotExist):
                messages.error(
                    request,
                    _("User profile does not contain all required fields. "
                        "Please update your profile.")
                    )
                return redirect('competitions_season_detail_latest')

            # save submission
            try:
                filelist = request.FILES.getlist('solution')
                submission.solution = convert_files_to_single_pdf(
                                          settings.SENDFILE_ROOT,
                                          submission.get_solution_path(),
                                          filelist)
                submission.user_modified_at = now()
                submission.save()

                # warn user if converting files could have gone wrong
                risky_extensions = ['.doc', '.docx']
                for file in filelist:
                    for extension in risky_extensions:
                        if file.name.endswith(extension):
                            messages.error(
                                request,
                                _('Converting %s files to .pdf sometimes does not work properly, '
                                    'please check the result!' %" ".join(risky_extensions))
                                )

            except ValidationError, e:
                messages.error(request, u'\n'.join(e.messages))

        else:
            for field, errors in form.errors.iteritems():
                messages.error(request, u"{error}".format(
                                    error=', '.join(errors))
                              )

        return redirect('competitions_season_detail_latest')


# TODO: make this view protected so that only staff members can use it
# TODO: make sure this gets proper treatement when row-level permissions are
#       introduced
class ImportCorrectedSolutionsView(View):

    form_class = ImportCorrectedSolutionsForm

    def get(self, request, *args, **kwargs):
        return render(request, 'admin/import_corrected_solutions.html',
                      {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            try:
                file_data = form.cleaned_data['zipfile']
                filepath = get_uploaded_filepath(file_data)
                solutions_zip = ZipFile(filepath)

                # Check for any corrupted files in the zip
                # testzip returns the list of corrupted ones
                if solutions_zip.testzip():
                    messages.error(request,
                                   '"%s" in the .zip archive is corrupt.'
                                   % solutions_zip.testzip())
                    raise Exception('Corrpted archive.')

                # We loop over all PDF files in the zip
                for filename in [name for name in solutions_zip.namelist()
                                 if name.endswith('.pdf')]:

                    # Check that the name is of the form
                    # <score>-<username>-<problem_pk>.pdf
                    try:
                        parts = filename.rstrip('.pdf').split('-')

                        score = int(parts[0])
                        username = '-'.join(parts[1:-1])
                        problem_pk = int(parts[-1])

                    except (IndexError, ValueError, AssertionError):
                        messages.error(request,
                                       '"%s" is not of the correct form '
                                       '<score>-<username>-<problem_pk>.pdf'
                                       % remove_accents(filename))
                        continue

                    # Find the UserSolution and modify it
                    try:
                        user = User.objects.get(username=username)
                        solution = UserSolution.objects.get(user=user,
                                                            problem=problem_pk)
                    except User.DoesNotExist:
                        messages.error('User %s does not exist' % username)
                        continue
                    except UserSolution.DoesNotExist:
                        messages.error(request,
                                       'Solution for user %s and problem '
                                       '%d does not exist.'
                                       % (username, problem_pk))
                        continue

                    extracted_path = solutions_zip.extract(filename, path='/tmp')
                    new_path = os.path.join(settings.SENDFILE_ROOT, solution.get_corrected_solution_path())
                    file_move_safe(extracted_path, new_path, allow_overwrite=True)

                    solution.score = score
                    solution.corrected_solution = solution.get_corrected_solution_path()
                    solution.save()

                    messages.success(
                        request,
                        _("%s assigned %d points") % (solution, score)
                    )

            except Exception, e:
                # If any exceptions happened, errors should be in messages
                messages.error(request, 'exception happened: %s' % e)
            finally:
                # redirect back to admin site
                return redirect('admin:problems_usersolution_changelist')

        else:
            return render(request, 'admin/import_corrected_solutions.html',
                          {'form': form})
