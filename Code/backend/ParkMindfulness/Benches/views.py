# view specific imports
from django.forms import model_to_dict
from rest_framework.response import Response
from .models import Benches, Audio
from Parks.models import Park
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView, DestroyAPIView, RetrieveAPIView
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ParseError
from django.shortcuts import get_object_or_404
from django.conf import settings
from ..ParkMindfulness.settings import DEBUG

# for image editing within QR
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# for handling file deletion within /media
import os

# qr code generation imports
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO


## Constants for QR
QR_NAME = "Ontario Parks"
QR_DESC = "Scan code with phone camera for Park Mindfulness Experience\nOR visit https://6-john-t-one.vercel.app"


##################
# BENCH CREATION #
##################

class BenchCreateView_admin(CreateAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BenchCreationSerializer
    
    def post(self, request, *args, **kwargs):
        
        # check that the entered park id exists in the database
        park = Park.objects.filter(park_id=request.data['park_id'])
        if not park.exists():
            return Response({"message": "The park id entered does not exist in the database"}, status=400)
        
        # check the bench title and thumbnail fields are not empty
        if not request.data['bench_title']:
            return Response({"message": "The bench title field cannot be empty"}, status=400)
        if not request.data['thumbnail']:
            return Response({"message": "The thumbnail field cannot be empty"}, status=400)
        
        # audio file is optional, so check if it exists to set the boolean field to true
        file = request.FILES.get('secondary_model.audio_file', None)

        bench_data = {
            'bench_title': request.data.get('bench_title', None),
            'thumbnail': request.data.get('thumbnail', None),
            'park_id': request.data.get('park_id', None),
        }

        audio_data = {
            # 'audio_file': request.data.get('secondary_model.audio_file', None),
            'contributor': request.data.get('secondary_model.contributor', None),
            'length_category': request.data.get('secondary_model.length_category', None),
            'season_category': request.data.get('secondary_model.season_category', None),
        }
        if file:
            audio_data['audio_binary'] = True
            audio_data['audio_file'] = file
        else:
            audio_data['audio_binary'] = False
            # if no audio file is provided, set all audio fields to null
            audio_data['contributor'] = None
            audio_data['length_category'] = None
            audio_data['season_category'] = None

        # take in the data from the request to create a new bench object
        # serializer = FullBenchCreationSerializer(data=request.data)
        serializer1 = NoAudioBenchCreationSerializer(data=bench_data)
        serializer2 = FullAudioSerializer(data=audio_data)

        # save the bench object in the database as is (no qr code yet)
        if not serializer1.is_valid():
            return Response({"message": "Bench creation failed (client error). Make sure to fill out all of the fields!"}, status=400)
        # otw
        bench = serializer1.save()
        
        # add bench id to the audio data and save the audio object in the database
        audio_data['bench_id'] = bench.bench_id
        if not serializer2.is_valid():
            return Response({"message": "Audio creation failed (client error). Make sure to fill out all of the fields!"}, status=400)
        
        serializer2.save()

        # create the qr code that is to identify this bench object when users scan it

        # build the front end link template that we are to make the QR code for
        # qr_link = f"https://6-john-t-one.vercel.app/#/media?m={bench.bench_id}&park_id={bench.park_id}"
        if DEBUG == True:
            qr_link = f"https://6-john-t-one.vercel.app/#/media?m={bench.bench_id}"
        else:
            qr_link = f"https://main--parkmindfulness-user.netlify.app/#/media?m={bench.bench_id}"

        # use the qrcode library to make a qr code image through teh qr_class class
        qr_class = qrcode.QRCode(version=1, box_size=30)
        qr_class.add_data(qr_link)
        qr_class.make(fit=True)

        bench_qr = qr_class.make_image(fill_color="black", back_color="white")

        # edit image
        draw = ImageDraw.Draw(bench_qr)
        font_path = os.path.join(settings.STATIC_ROOT, 'fonts/ourfont.ttf')
        draw.text((50,25), QR_NAME, fill="black", font=ImageFont.truetype(font_path, size=42))
        draw.text((185,1100), QR_DESC, fill="black", font=ImageFont.truetype(font_path, size=30), align="center")

        # save the image to a buffer in PNG format
        buffer = BytesIO()
        bench_qr.save(buffer, format='PNG')
        
        # save the qr code from the buffer to the bench object in the database
        bench.qr_code.save(f"qr_code_{bench.bench_id}.png", ContentFile(buffer.getvalue()), save=True)

        return Response({"message": "Bench object has been created!"}, status=201)


#########################################
# BENCH VIEWING  (park and bench based) #
#########################################

# Note that the admin and user views are basically the same, but they do differ in the 
# fact that the admin get requires an authenticated user, and returns the bench's QR code
# too. On all other aspects, they are the same.
 
# The view to get the bench in the database corresponding to the given bench id (for admins)
class BenchGetView_admin(RetrieveAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BenchViewSerializer_admin  # the serializer that shows all the details
    
    def get(self, request, *args, **kwargs):
        """
        Contract with admin frontend: given bench_id, must return:
        - title of bench
        - author of bench  # TODO
        - link to audio file on server  # TODO
        - link to image file on server
        - link to QR code file
        - a boolean that tells you if there is a audio file or not  # TODO
        """
        # fetch the bench id from the request kwargs
        bench_to_display = self.kwargs['bench_id']

        # fetch the audio object from the database
        audio_object = Audio.objects.filter(bench_id=bench_to_display).first()
        # we know audio_object exists given the way the creation is done

        # get the bench in the database with the given bench id or raise a 404 (not found) error
        bench = get_object_or_404(Benches, bench_id=bench_to_display)

        # serialize the bench and audio objects separately
        bench_data = self.serializer_class(bench).data
        audio_data = BenchViewAudioSerializer_admin(audio_object).data

        bench_data['audio_details'] = audio_data

        return Response(bench_data, status=200)
    
# The view to get the bench in the database corresponding to the given bench id (for users)
class BenchGetView_user(RetrieveAPIView):

    serializer_class = BasicBenchSerializer  # the serializer that shows all the details
    
    def get(self, request, *args, **kwargs):
        """
        Contract with frontend user: given bench_id, must return:
        - title of bench
        - author of bench
        - link to audio file on server (if exists)
        - a boolean that tells us if there is a audio file or not
        - link to image file on server
        """
        # fetch the bench id from the request kwargs
        bench_to_display = self.kwargs['bench_id']

        # fetch the audio object from the database
        audio_object = Audio.objects.filter(bench_id=bench_to_display).first()
        # we know audio_object exists given the way the creation is done

        # get the bench in the database with the given bench id or raise a 404 (not found) error
        bench = get_object_or_404(Benches, bench_id=bench_to_display)

        # serialize the bench object
        bench_data = self.serializer_class(bench).data
        audio_data = BenchViewAudioSerializer_user(audio_object).data

        bench_data['audio_details'] = audio_data

        return Response(bench_data, status=200)


# The view to get all the benches in the database corresponding to the given park id
class BenchGetAllView_admin(ListAPIView):

    queryset = Benches.objects.all()  # dummy queryset to trick the ListAPIView
    permission_classes = [IsAuthenticated]
    serializer_class = BenchViewSerializer_admin  # the serializer that shows all the details

    def list(self, request, *args, **kwargs):

        # The method actually handling the GET request. By not being the get_queryset method,
        # its not limited to just returning a queryset, so it lets us add the audio details
        # to the response.
        
        park_to_display = self.kwargs['park_id']
        benches = Benches.objects.filter(park_id=park_to_display)
        get_object_or_404(Park, park_id=park_to_display)

        if not benches.exists():
            raise ParseError({"message": "There are no benches in this park"})

        benches_data = []
        for bench in benches:
            audio_object = Audio.objects.filter(bench_id=bench.bench_id).first()
            audio_data = BenchViewAudioSerializer_admin(audio_object).data
            bench_data = self.serializer_class(bench).data
            bench_data['audio_details'] = audio_data
            benches_data.append(bench_data)
        return Response(benches_data)

        
# # The view to get all Parks in the database
# class ParkGetAllView_admin(ListAPIView):

#     # permission_classes = [IsAuthenticated]
#     serializer_class = ParkViewSerializer  # the serializer that shows all the details
    
#     def get_queryset(self):
#         # get all parks in the database
#         parks = Park.objects.all()
#         if parks.exists():
#             return parks.order_by('park_id')
#         else: 
#             # the park exists but there are no benches in the database, so return an empty list
#             return []


##################
# BENCH UPDATING #
##################

# The view to update a bench object in the database (can only update the name, audio, author, and thumbnail)
class BenchUpdateView_admin(UpdateAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = BenchUpdateSerializer
    
    def put(self, request, *args, **kwargs):  # behaves like a post request
        ### NOTE: that leaving the audio fields empty => audio file erased
        ###       leaving the other bench fields empty => original values kept

        bench_data = {
            'bench_title': request.data.get('bench_title', None),
            'thumbnail': request.data.get('thumbnail', None),
        }

        audio_data = {
            # 'audio_file': request.data.get('secondary_model.audio_file', None),
            'contributor': request.data.get('secondary_model.contributor', None),
            'length_category': request.data.get('secondary_model.length_category', None),
            'season_category': request.data.get('secondary_model.season_category', None),
        }

        # otw, fetch the bench id from the request kwargs and get the object from DB
        bench_to_update = self.kwargs['bench_id']  
        bench = get_object_or_404(Benches, bench_id=bench_to_update)
        audio = get_object_or_404(Audio, bench_id=bench_to_update)

        # determine which fields are to be updated, whichever field has been left empty should not be
        # erased, but rather keep the original value
        if not request.data['bench_title']:
            bench_data['bench_title'] = bench.bench_title
        if not request.data['thumbnail']:
            bench_data['thumbnail'] = bench.thumbnail
        
        # check for the update on the audios, a file can be updated without necessarily updating the
        # author, length, or season, this is left to the discretion of the user
        # if the file is not updated though, then the author, length or season should not be updated
        file = request.FILES.get('secondary_model.audio_file', None)
        if not file:
            # updating to delete the audio file => all None
            audio_data['audio_binary'] = False
            audio_data['audio_file'] = None
            audio_data['contributor'] = None
            audio_data['length_category'] = None
            audio_data['season_category'] = None
        else:
            # update file, update other args as needed by user
            audio_data['audio_file'] = file
            audio_data['audio_binary'] = True
            if not request.data['secondary_model.contributor']:
                audio_data['contributor'] = audio.contributor
            if not request.data['secondary_model.length_category']:
                audio_data['length_category'] = audio.length_category
            if not request.data['secondary_model.season_category']:
                audio_data['season_category'] = audio.season_category


        # take in the data from the request to update the bench object
        serializer1 = BasicBenchSerializer(bench, data=bench_data, partial=True)
        serializer2 = FullAudioSerializer(audio, data=audio_data, partial=True)

        if not serializer1.is_valid() or not serializer2.is_valid():
            # print errors
            # print(serializer.errors)
            return Response({"message": "Bench update could not go through (client error)!"}, status=400)

        if bench:
            # then we can update the bench object (the first and only one that should exist) with the given data
            serializer1.update(bench, serializer1.validated_data)
            serializer2.update(audio, serializer2.validated_data)
            return Response({"message": "Bench object has been updated!"}, status=200)
        else:
            # Return not found error message
            return Response({"message": "No bench found for the given bench id"}, status=404)


##################
# BENCH DELETION #
##################

# The view to delete a bench object in the database
class BenchDeleteView_admin(DestroyAPIView):
    
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        print("HERE")
        # fetch the bench id from the request kwargs
        bench_to_delete = self.kwargs['bench_id']
        # get the bench object with the given bench id
        bench = Benches.objects.filter(bench_id=bench_to_delete)

        if bench.exists():
            # get the names of the files within the media folder to be deleted
            bench = bench.first()
            bench_thumbnail = bench.thumbnail
            bench_qr = bench.qr_code
            audio = Audio.objects.filter(bench_id=bench_to_delete)
            print(audio)

            # delete the files from the media folder
            thumbnail_path = os.path.join(settings.MEDIA_ROOT, bench_thumbnail.name)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            qr_path = os.path.join(settings.MEDIA_ROOT, bench_qr.name)
            if os.path.exists(qr_path):
                os.remove(qr_path)
            
            
            # next, delete the audio file
            if audio.exists():
                audio = get_object_or_404(Audio, bench_id=bench_to_delete)
                if audio.audio_binary:
                    # only when a file is registered in the database, delete it
                    audio_file = audio.audio_file
                    audio_path = os.path.join(settings.MEDIA_ROOT, audio_file.name)
                    print(audio_path)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
            
            # finally, say bye bye to the bench and audio objects
            audio.delete()
            bench.delete()
            return Response({"message": "Bench object has been deleted!"}, status=200)
        else:
            # Return not found error message if no corresponding bench is found
            return Response({"message": "No bench found for the given bench id"}, status=404)

